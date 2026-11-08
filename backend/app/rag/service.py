import asyncio
import hashlib
import logging
from time import perf_counter
from uuid import NAMESPACE_URL, uuid5

from sqlalchemy.exc import SQLAlchemyError

from app.core.exceptions import AppError
from app.core.logging import request_id_context
from app.integrations.rag.interface import RetrievalResult, RetrievedDocument
from app.rag.embeddings import validate_vectors
from app.rag.extraction import chunk_sections, extract, normalized
from app.rag.identifiers import component_identifiers, contains_identifier
from app.rag.query_expansion import QueryExpander
from app.rag.ranking import rerank
from app.rag.schemas import IngestionReport

logger = logging.getLogger(__name__)


class RagService:
    def __init__(self, knowledge, embeddings, settings, *, query_expander=None):
        self.knowledge, self.embeddings, self.settings = knowledge, embeddings, settings
        self.extraction_slots = asyncio.Semaphore(2)
        self.query_expander = query_expander or (
            QueryExpander(settings)
            if settings.rag_query_expansion_enabled and settings.openai_api_key
            else None
        )

    async def ingest(self, filename, content_type, content, metadata, *, source_page_start=1):
        if not content or len(content) > self.settings.document_max_bytes:
            raise AppError(413, "document_size", "Document is empty or exceeds the upload limit.")
        if metadata.license_status != "authorized" or metadata.verification_status == "rejected":
            raise AppError(
                422, "source_not_authorized", "Confirm indexing permission before upload."
            )
        content_hash = hashlib.sha256(content).hexdigest()
        identifier = uuid5(NAMESPACE_URL, "ai-car-document:" + content_hash)
        warnings, chunks, failure = [], [], None
        try:
            async with self.extraction_slots, asyncio.timeout(15):
                kind, sections, warnings = await asyncio.to_thread(
                    extract,
                    filename,
                    content_type,
                    content,
                    self.settings,
                    source_page_start=source_page_start,
                )
                if kind != metadata.document_type:
                    raise AppError(
                        422, "content_type_mismatch", "Metadata type differs from the file."
                    )
                chunks = chunk_sections(
                    identifier, sections, self.settings.chunk_size, self.settings.chunk_overlap
                )
        except TimeoutError:
            failure = "extraction_timeout"
        except AppError as exc:
            failure = exc.code
        doc_id, created, count = await self.knowledge.ingest(
            metadata, content_hash, chunks if not failure else [], error_code=failure
        )
        return IngestionReport(
            document_id=doc_id,
            status=("duplicate" if not created else "failed" if failure else "processed"),
            chunk_count=count,
            error_code=failure,
            warnings=warnings,
        )

    async def index(self, identifier):
        document, chunks = await self.knowledge.get(identifier)
        if (
            document["license_status"] != "authorized"
            or document["verification_status"] != "verified"
        ):
            raise AppError(422, "source_not_authorized", "This source cannot be indexed.")
        if document["ingestion_status"] != "processed" or not chunks:
            raise AppError(422, "document_not_extracted", "Extract document text before indexing.")
        vectors = await self.embeddings.embed([chunk["text"] for chunk in chunks])
        try:
            validate_vectors(vectors, len(chunks), self.settings.embedding_dimensions)
        except (ValueError, TypeError):
            raise AppError(
                502, "invalid_embeddings", "Invalid embedding output; nothing was saved."
            ) from None
        await self.knowledge.save_vectors(
            identifier, chunks, vectors, self.embeddings.model, self.settings.embedding_dimensions
        )
        return {
            "document_id": identifier,
            "indexed_chunks": len(chunks),
            "embedding_model": self.embeddings.model,
            "embedding_dimensions": self.settings.embedding_dimensions,
        }

    async def retrieve(self, vehicle, query, technical_context=None):
        started = perf_counter()
        if not self.settings.rag_enabled:
            return RetrievalResult(available=False, reason="Retrieval is disabled.")
        try:
            async with asyncio.timeout(self.settings.rag_timeout_seconds):
                context = (technical_context or {}).get("symptoms", "")
                text = " ".join(normalized(query + " " + context).split())[:6000]
                if not text:
                    raise AppError(422, "empty_query", "A retrieval query is required.")
                queries = [text]
                if self.query_expander:
                    queries.extend(await self.query_expander.expand(text))
                queries = list(
                    dict.fromkeys(" ".join(normalized(query).split())[:6000] for query in queries)
                )[:3]
                vectors = await self.embeddings.embed(queries)
                validate_vectors(vectors, len(queries), self.settings.embedding_dimensions)
                requested_identifiers = component_identifiers(query)
                use_lexical = self.settings.rag_lexical_weight > 0 and not requested_identifiers
                candidate_limit = (
                    max(self.settings.rag_top_k, self.settings.rag_rerank_candidates)
                    if use_lexical
                    else self.settings.rag_top_k
                )
                rows, count, missing_code, foreign = await self.knowledge.search(
                    vehicle,
                    vectors[0],
                    self.embeddings.model,
                    self.settings.embedding_dimensions,
                    candidate_limit,
                    self.settings.rag_min_similarity,
                    allow_related_volkswagen=self.settings.rag_allow_related_volkswagen,
                    additional_vectors=vectors[1:],
                    requested_identifiers=requested_identifiers,
                )
                documents = [RetrievedDocument.model_validate(row) for row in rows]
                if any(document.citation is None for document in documents):
                    raise ValueError("Retrieved chunks require source metadata")
                if use_lexical:
                    documents = rerank(
                        documents,
                        queries,
                        self.settings.rag_top_k,
                        weight=self.settings.rag_lexical_weight,
                    )
                reasons = []
                uncovered = [
                    code
                    for code in requested_identifiers
                    if not any(contains_identifier(doc.relevant_text, code) for doc in documents)
                ]
                if uncovered:
                    reasons.append(
                        "No retrieved passage explicitly mentions: "
                        + ", ".join(uncovered)
                        + ". Do not substitute different component identifiers."
                    )
                if any(
                    doc.relevance_metadata.get("reference_scope") == "related_volkswagen_learning"
                    for doc in documents
                ):
                    reasons.append(
                        "Related Volkswagen documents are learning references; their procedures, "
                        "specifications and part fitment are not verified for this vehicle."
                    )
                if not documents:
                    reasons.append("No sufficient compatible technical evidence was retrieved.")
                if any(
                    doc.citation.evidence_type in {"official_manufacturer", "third_party_technical"}
                    for doc in documents
                ):
                    reasons.append(
                        "The gearbox code and equipment PR codes are not confirmed. "
                        "Matching year/engine metadata does not establish gearbox, brake "
                        "configuration or part compatibility. "
                        "Text-extracted diagram labels do not verify wire paths, pin-to-pin "
                        "connections, fuse assignments or table column associations; "
                        "visual source review and variant confirmation are required."
                    )
                if any(
                    doc.citation.evidence_type in {"generic_reference", "internal_demo"}
                    for doc in documents
                ):
                    reasons.append(
                        "Generic/demo material is not verified manufacturer documentation."
                    )
                if foreign:
                    reasons.append(
                        "Documents using other embedding models were excluded; reindex them."
                    )
                if missing_code:
                    reasons.append(
                        "Engine-code-specific documentation was excluded: engine_code is unknown."
                    )
                result = RetrievalResult(
                    available=True,
                    documents=documents,
                    reason=" ".join(reasons) or None,
                    candidate_count=count,
                    missing_vehicle_fields=["engine_code"] if missing_code else [],
                )
        except (AppError, SQLAlchemyError, TimeoutError, ValueError, TypeError):
            result = RetrievalResult(
                available=False,
                reason="Verified technical evidence was not retrieved; retrieval is unavailable.",
            )
        result.latency_ms = round((perf_counter() - started) * 1000, 3)
        logger.info(
            "retrieval request_id=%s available=%s candidates=%s selected=%s "
            "duration_ms=%s filters=vehicle",
            request_id_context.get(),
            result.available,
            result.candidate_count,
            len(result.documents),
            result.latency_ms,
        )
        return result


def validated_citations(identifiers, result):
    allowed = {
        document.citation.chunk_id: document.citation
        for document in result.documents
        if document.citation is not None
    }
    if any(identifier not in allowed for identifier in identifiers):
        raise AppError(502, "invalid_citations", "AI citations did not match retrieved evidence.")
    return [allowed[identifier] for identifier in dict.fromkeys(identifiers)]
