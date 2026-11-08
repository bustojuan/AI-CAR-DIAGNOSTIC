from uuid import NAMESPACE_URL, uuid5

from sqlalchemy import and_, case, delete, func, or_, select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.orm import defer

from app.core.exceptions import AppError, not_found
from app.database.models import DiagnosticRow
from app.database.models import DocumentChunkRow as Chunk
from app.database.models import TechnicalDocumentRow as Document
from app.rag.compatibility import compatible, related_volkswagen_predicates, vehicle_predicates
from app.rag.identifiers import contains_identifier, identifier_pattern
from app.rag.schemas import SourceCitation


class PostgresKnowledgeStore:
    def __init__(self, store):
        self.store = store

    def sessions(self):
        self.store.connect()
        return self.store.sessions()

    async def ingest(self, metadata, content_hash, chunks, *, error_code=None):
        identifier = uuid5(NAMESPACE_URL, "ai-car-document:" + content_hash)
        data = metadata.model_dump()
        data.update(
            id=identifier,
            content_hash=content_hash,
            storage_path=None,
            ingestion_status="failed" if error_code else "processed",
            extraction_error=error_code,
        )
        async with self.sessions() as session, session.begin():
            created = await session.scalar(
                insert(Document)
                .values(**data)
                .on_conflict_do_nothing(index_elements=[Document.content_hash])
                .returning(Document.id)
            )
            if created is None:
                existing = await session.scalar(
                    select(Document).where(Document.content_hash == content_hash)
                )
                count = await session.scalar(
                    select(func.count()).select_from(Chunk).where(Chunk.document_id == existing.id)
                )
                return existing.id, False, count
            session.add_all(
                [
                    Chunk(
                        id=chunk.chunk_id,
                        document_id=identifier,
                        chunk_index=chunk.chunk_index,
                        content=chunk.text,
                        content_hash=chunk.content_hash,
                        page_number=chunk.page,
                        section=chunk.section,
                    )
                    for chunk in chunks
                ]
            )
        return identifier, True, len(chunks)

    async def list(self, limit=100, offset=0):
        async with self.sessions() as session:
            rows = await session.scalars(
                select(Document).order_by(Document.id).limit(limit).offset(offset)
            )
            return [self.metadata(row) for row in rows]

    @staticmethod
    def metadata(row):
        return {column.name: getattr(row, column.name) for column in Document.__table__.columns}

    async def get(self, identifier):
        async with self.sessions() as session:
            row = await session.get(Document, identifier)
            if not row:
                raise not_found("Document")
            chunks = list(
                await session.scalars(
                    select(Chunk).where(Chunk.document_id == identifier).order_by(Chunk.chunk_index)
                )
            )
            return self.metadata(row), [
                dict(
                    chunk_id=c.id,
                    text=c.content,
                    content_hash=c.content_hash,
                    page=c.page_number,
                    section=c.section,
                )
                for c in chunks
            ]

    async def delete(self, identifier):
        async with self.sessions() as session, session.begin():
            result = await session.execute(delete(Document).where(Document.id == identifier))
            if not result.rowcount:
                raise not_found("Document")

    async def save_vectors(self, identifier, snapshot, vectors, model, dimensions):
        async with self.sessions() as session, session.begin():
            document = await session.scalar(
                select(Document).where(Document.id == identifier).with_for_update()
            )
            if not document:
                raise not_found("Document")
            if (
                document.license_status != "authorized"
                or document.verification_status != "verified"
            ):
                raise AppError(
                    409, "document_permission_changed", "Source is no longer eligible for indexing."
                )
            chunks = list(
                await session.scalars(
                    select(Chunk).where(Chunk.document_id == identifier).order_by(Chunk.chunk_index)
                )
            )
            if [(c.id, c.content_hash) for c in chunks] != [
                (c["chunk_id"], c["content_hash"]) for c in snapshot
            ]:
                raise AppError(409, "document_changed", "Document changed during indexing; retry.")
            for chunk, vector in zip(chunks, vectors, strict=True):
                chunk.embedding, chunk.embedding_model = vector, model
                chunk.embedding_dimensions = dimensions
            await session.flush()

    async def replace_unindexed_chunks(self, identifier, content_hash, snapshot, chunks):
        """Explicit local re-extraction only; never rewrite indexed or cited evidence."""
        async with self.sessions() as session, session.begin():
            document = await session.scalar(
                select(Document).where(Document.id == identifier).with_for_update()
            )
            if not document:
                raise not_found("Document")
            if document.content_hash != content_hash or document.license_status != "authorized":
                raise AppError(409, "source_changed", "Source identity or permission changed.")
            if document.verification_status == "rejected":
                raise AppError(409, "source_rejected", "Rejected sources cannot be re-extracted.")
            stored = list(
                await session.scalars(
                    select(Chunk).where(Chunk.document_id == identifier).order_by(Chunk.chunk_index)
                )
            )
            if [(c.id, c.content_hash) for c in stored] != [
                (c["chunk_id"], c["content_hash"]) for c in snapshot
            ]:
                raise AppError(409, "document_changed", "Chunks changed; repeat the preflight.")
            if any(c.embedding is not None for c in stored):
                raise AppError(409, "source_already_indexed", "Indexed evidence must be retained.")
            cited = await session.scalar(
                select(DiagnosticRow.id)
                .where(DiagnosticRow.citations.contains([{"document_id": str(identifier)}]))
                .limit(1)
            )
            if cited:
                raise AppError(
                    409, "source_already_cited", "Historical citations must be retained."
                )
            if not chunks:
                raise AppError(422, "empty_extraction", "New extraction cannot be empty.")
            await session.execute(delete(Chunk).where(Chunk.document_id == identifier))
            session.add_all(
                [
                    Chunk(
                        id=c.chunk_id,
                        document_id=identifier,
                        chunk_index=c.chunk_index,
                        content=c.text,
                        content_hash=c.content_hash,
                        page_number=c.page,
                        section=c.section,
                    )
                    for c in chunks
                ]
            )
            await session.flush()

    async def stats(self):
        async with self.sessions() as session:
            documents = await session.scalar(select(func.count()).select_from(Document))
            chunks = await session.scalar(select(func.count()).select_from(Chunk))
            indexed = await session.scalar(
                select(func.count()).select_from(Chunk).where(Chunk.embedding.is_not(None))
            )
            models = list(
                await session.scalars(
                    select(Chunk.embedding_model).where(Chunk.embedding.is_not(None)).distinct()
                )
            )
            return dict(
                documents=documents, chunks=chunks, indexed_chunks=indexed, embedding_models=models
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
        distance = Chunk.embedding.cosine_distance(vector)
        if additional_vectors:
            distance = func.least(
                distance,
                *[Chunk.embedding.cosine_distance(variant) for variant in additional_vectors[:2]],
            )
        eligible = [
            Document.license_status == "authorized",
            Document.verification_status == "verified",
            Document.ingestion_status == "processed",
            Chunk.embedding.is_not(None),
            Chunk.embedding_model == model,
            Chunk.embedding_dimensions == dimensions,
        ]
        specific = Document.manufacturer.is_not(None)
        exact = and_(*vehicle_predicates(Document, vehicle))
        scope = (
            or_(exact, and_(*related_volkswagen_predicates(Document, vehicle)))
            if allow_related_volkswagen
            else exact
        )
        # Compatibility is an eligibility gate, not a substitute for relevance.
        # Prefer source specificity only for equal distances; otherwise weak
        # vehicle-matching passages can displace relevant eligible references.
        ordering = (distance, exact.desc(), specific.desc(), Chunk.id)
        if requested_identifiers:
            code_matches = sum(
                case((Chunk.content.op("~*")(identifier_pattern(code)), 1), else_=0)
                for code in requested_identifiers[:8]
            )
            eligible.append(code_matches > 0)
            ordering = (code_matches.desc(), *ordering)
        # Deduplicate before limiting so repeated paragraphs cannot hide evidence.
        ranked = (
            select(
                Chunk.id.label("chunk_id"),
                func.row_number()
                .over(
                    partition_by=Chunk.content_hash,
                    order_by=ordering,
                )
                .label("duplicate_rank"),
            )
            .join(Document)
            .where(
                *eligible,
                scope,
                distance <= 1 - minimum,
            )
            .subquery()
        )
        statement = (
            select(Chunk, Document, distance.label("distance"))
            .options(defer(Chunk.embedding))
            .join(Document)
            .join(ranked, ranked.c.chunk_id == Chunk.id)
            .where(ranked.c.duplicate_rank == 1)
            .order_by(*ordering)
            .limit(limit)
        )
        async with self.sessions() as session:
            rows = (await session.execute(statement)).all()
            requires_code = False
            if vehicle.engine_code is None:
                requires_code = bool(
                    await session.scalar(
                        select(Chunk.id)
                        .join(Document)
                        .where(
                            *eligible,
                            *vehicle_predicates(Document, vehicle, skip_engine_code=True),
                            Document.engine_code.is_not(None),
                            distance <= 1 - minimum,
                        )
                        .limit(1)
                    )
                )
            foreign_models = list(
                await session.scalars(
                    select(Chunk.embedding_model)
                    .where(Chunk.embedding.is_not(None), Chunk.embedding_model != model)
                    .distinct()
                )
            )
        output, seen = [], set()
        for chunk, document, score in rows:
            if chunk.content_hash in seen:
                continue
            seen.add(chunk.content_hash)
            citation = SourceCitation(
                document_id=document.id,
                chunk_id=chunk.id,
                document_title=document.title,
                publisher=document.publisher,
                source_url=(document.source_url if document.public_source_url else None),
                page=chunk.page_number,
                section=chunk.section,
                evidence_type=document.evidence_type,
                verification_status=document.verification_status,
            )
            output.append(
                dict(
                    document_id=document.id,
                    title=document.title,
                    source=document.source_name,
                    relevant_text=chunk.content,
                    page=chunk.page_number,
                    section=chunk.section,
                    citation=citation,
                    relevance_metadata={
                        "cosine_similarity": 1 - float(score),
                        "matched_identifiers": ", ".join(
                            code
                            for code in requested_identifiers
                            if contains_identifier(chunk.content, code)
                        ),
                        "query_strategy": "multilingual_max_similarity"
                        if additional_vectors
                        else "semantic",
                        "reference_scope": (
                            "matching_vehicle_metadata"
                            if compatible(document, vehicle)
                            else "related_volkswagen_learning"
                        ),
                        "source_model": document.model or "unspecified",
                        "source_engine": document.engine or "unspecified",
                        "source_engine_code": document.engine_code or "unspecified",
                    },
                )
            )
            if len(output) == limit:
                break
        return output, len(rows), requires_code, foreign_models
