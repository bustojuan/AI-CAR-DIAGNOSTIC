"""Test-only stores/vectors. Never used by application startup or real evaluation."""

import math
from types import SimpleNamespace
from uuid import NAMESPACE_URL, uuid5

from app.core.exceptions import not_found
from app.rag.compatibility import compatible, related_volkswagen
from app.rag.identifiers import contains_identifier
from app.rag.schemas import SourceCitation


class FakeEmbeddings:
    model = "fixture-embeddings"
    dimensions = 4

    def __init__(self):
        self.calls, self.failure = [], None

    async def embed(self, texts):
        self.calls.append(texts)
        if self.failure:
            raise self.failure
        output = []
        for text in texts:
            value = text.casefold()
            index = (
                0
                if "battery" in value or "crank" in value
                else 1
                if "glow" in value
                else 2
                if "cool" in value
                else 3
            )
            vector = [0.0] * 4
            vector[index] = 1.0
            output.append(vector)
        return output


class FakeKnowledge:
    def __init__(self):
        self.documents, self.chunks, self.vectors = {}, {}, {}

    async def ingest(self, metadata, content_hash, chunks, *, error_code=None):
        identifier = uuid5(NAMESPACE_URL, "ai-car-document:" + content_hash)
        if identifier in self.documents:
            return identifier, False, len(self.chunks[identifier])
        self.documents[identifier] = {
            **metadata.model_dump(),
            "id": identifier,
            "content_hash": content_hash,
            "ingestion_status": "failed" if error_code else "processed",
            "extraction_error": error_code,
        }
        self.chunks[identifier] = [
            dict(
                chunk_id=c.chunk_id,
                text=c.text,
                content_hash=c.content_hash,
                page=c.page,
                section=c.section,
            )
            for c in chunks
        ]
        return identifier, True, len(chunks)

    async def get(self, identifier):
        if identifier not in self.documents:
            raise not_found("Document")
        return self.documents[identifier], self.chunks[identifier]

    async def list(self, limit=100, offset=0):
        return list(self.documents.values())[offset : offset + limit]

    async def delete(self, identifier):
        if identifier not in self.documents:
            raise not_found("Document")
        self.documents.pop(identifier)
        for chunk in self.chunks.pop(identifier):
            self.vectors.pop(chunk["chunk_id"], None)

    async def save_vectors(self, identifier, snapshot, vectors, model, dimensions):
        for chunk, vector in zip(snapshot, vectors, strict=True):
            self.vectors[chunk["chunk_id"]] = vector, model, dimensions

    async def stats(self):
        return dict(
            documents=len(self.documents),
            chunks=sum(map(len, self.chunks.values())),
            indexed_chunks=len(self.vectors),
            embedding_models=list({v[1] for v in self.vectors.values()}),
        )

    async def search(
        self,
        vehicle,
        vector,
        model,
        dimensions,
        limit,
        minimum,
        *,
        allow_related_volkswagen=False,
        additional_vectors=None,
        requested_identifiers=(),
    ):
        result, missing = [], False
        for identifier, metadata in self.documents.items():
            if (
                metadata["license_status"] != "authorized"
                or metadata["verification_status"] != "verified"
            ):
                continue
            for chunk in self.chunks[identifier]:
                if requested_identifiers and not any(
                    contains_identifier(chunk["text"], code) for code in requested_identifiers
                ):
                    continue
                saved = self.vectors.get(chunk["chunk_id"])
                if not saved or saved[1:] != (model, dimensions):
                    continue
                score = max(
                    sum(a * b for a, b in zip(saved[0], query, strict=True))
                    / (
                        math.sqrt(sum(a * a for a in saved[0]))
                        * math.sqrt(sum(b * b for b in query))
                    )
                    for query in [vector, *(additional_vectors or [])[:2]]
                )
                if score < minimum:
                    continue
                exact = compatible(SimpleNamespace(**metadata), vehicle)
                if not exact and not (
                    allow_related_volkswagen
                    and related_volkswagen(SimpleNamespace(**metadata), vehicle)
                ):
                    missing |= metadata["engine_code"] is not None and vehicle.engine_code is None
                    continue
                citation = SourceCitation(
                    document_id=identifier,
                    chunk_id=chunk["chunk_id"],
                    document_title=metadata["title"],
                    publisher=metadata["publisher"],
                    source_url=metadata["source_url"] if metadata["public_source_url"] else None,
                    page=chunk["page"],
                    section=chunk["section"],
                    evidence_type=metadata["evidence_type"],
                    verification_status=metadata["verification_status"],
                )
                result.append(
                    (
                        metadata["manufacturer"] is not None,
                        score,
                        dict(
                            document_id=identifier,
                            title=metadata["title"],
                            source=metadata["source_name"],
                            relevant_text=chunk["text"],
                            page=chunk["page"],
                            section=chunk["section"],
                            citation=citation,
                            relevance_metadata={
                                "cosine_similarity": score,
                                "reference_scope": (
                                    "matching_vehicle_metadata"
                                    if exact
                                    else "related_volkswagen_learning"
                                ),
                                "source_model": metadata["model"] or "unspecified",
                                "source_engine": metadata["engine"] or "unspecified",
                                "source_engine_code": metadata["engine_code"] or "unspecified",
                            },
                        ),
                    )
                )
        result.sort(
            key=lambda item: (
                -sum(
                    contains_identifier(item[2]["relevant_text"], code)
                    for code in requested_identifiers
                ),
                -item[1],
                item[2]["relevance_metadata"]["reference_scope"] != "matching_vehicle_metadata",
                -item[0],
                str(item[2]["citation"].chunk_id),
            )
        )
        return [item[2] for item in result[:limit]], len(result), missing, []
