from uuid import uuid4

import pytest
from sqlalchemy import text
from sqlalchemy.exc import DBAPIError, IntegrityError

from app.database.models import DocumentChunkRow, TechnicalDocumentRow
from app.database.schemas import ChunkCreate, DocumentCreate
from app.repositories.documents import PostgresDocumentRepository
from app.repositories.postgres import PostgresStore

pytestmark = pytest.mark.database


def sample_document(**updates):
    return DocumentCreate(
        title="Schema test only",
        source_name="Internal test fixture",
        document_type="markdown",
        evidence_type="internal_demo",
        language="en",
        content_hash="a" * 64,
        **updates,
    )


async def test_document_metadata_nullable_embedding_and_provenance(db_settings):
    store = PostgresStore(db_settings)
    try:
        await store.initialize()
        async with store.sessions() as session, session.begin():
            repository = PostgresDocumentRepository(session, 1536)
            document_id = await repository.add_document(sample_document())
            chunk_id = await repository.add_chunk(
                ChunkCreate(
                    document_id=document_id,
                    chunk_index=0,
                    content="Internal schema fixture.",
                    content_hash="b" * 64,
                    page_number=1,
                    section="Test",
                )
            )
        async with store.sessions() as session:
            document = await session.get(TechnicalDocumentRow, document_id)
            chunk = await session.get(DocumentChunkRow, chunk_id)
            assert document.manufacturer is None and document.model is None
            assert document.evidence_type == "internal_demo"
            assert document.verification_status == "unverified"
            assert chunk.embedding is None and chunk.embedding_model is None
            assert chunk.embedding_dimensions is None and chunk.section == "Test"
    finally:
        await store.close()


async def test_duplicate_chunk_index_and_document_hash_rejected(db_settings):
    store = PostgresStore(db_settings)
    try:
        await store.initialize()
        async with store.sessions() as session, session.begin():
            repo = PostgresDocumentRepository(session, 1536)
            document_id = await repo.add_document(sample_document())
            chunk = ChunkCreate(
                document_id=document_id, chunk_index=0, content="Test", content_hash="b" * 64
            )
            await repo.add_chunk(chunk)
        with pytest.raises(IntegrityError):
            async with store.sessions() as session, session.begin():
                await PostgresDocumentRepository(session, 1536).add_chunk(chunk)
        with pytest.raises(IntegrityError):
            async with store.sessions() as session, session.begin():
                await PostgresDocumentRepository(session, 1536).add_document(sample_document())
    finally:
        await store.close()


async def test_pgvector_storage_and_dimension_constraint(db_settings):
    # Synthetic storage fixture only. No embedding model is called or implemented.
    store = PostgresStore(db_settings)
    try:
        await store.initialize()
        async with store.sessions() as session, session.begin():
            repo = PostgresDocumentRepository(session, 1536)
            document_id = await repo.add_document(sample_document())
            chunk_id = await repo.add_chunk(
                ChunkCreate(
                    document_id=document_id,
                    chunk_index=0,
                    content="Dimension test",
                    content_hash="b" * 64,
                    embedding=[0.0] * 1536,
                    embedding_model="synthetic-storage-test",
                    embedding_dimensions=1536,
                )
            )
        async with store.sessions() as session:
            assert (
                await session.scalar(
                    text("SELECT vector_dims(embedding) FROM document_chunks WHERE id=:id"),
                    {"id": chunk_id},
                )
                == 1536
            )
        with pytest.raises(ValueError):
            async with store.sessions() as session, session.begin():
                await PostgresDocumentRepository(session, 1536).add_chunk(
                    ChunkCreate(
                        document_id=document_id,
                        chunk_index=1,
                        content="Invalid dimensions",
                        content_hash="c" * 64,
                        embedding=[0.0] * 3,
                        embedding_model="synthetic-storage-test",
                        embedding_dimensions=3,
                    )
                )
        with pytest.raises(DBAPIError) as failure:
            async with store.sessions() as session, session.begin():
                await session.execute(
                    text("UPDATE document_chunks SET embedding='[1,2,3]' WHERE id=:id"),
                    {"id": chunk_id},
                )
        assert "expected 1536 dimensions" in str(failure.value).lower()
    finally:
        await store.close()


async def test_generic_vehicle_scope_constraint_cannot_be_bypassed(db_settings):
    store = PostgresStore(db_settings)
    try:
        await store.initialize()
        with pytest.raises(IntegrityError):
            async with store.sessions() as session, session.begin():
                session.add(
                    TechnicalDocumentRow(
                        **{
                            **sample_document().model_dump(),
                            "id": uuid4(),
                            "manufacturer": "Volkswagen",
                        }
                    )
                )
                await session.flush()
    finally:
        await store.close()
