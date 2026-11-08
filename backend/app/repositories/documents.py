from app.database.models import DocumentChunkRow, TechnicalDocumentRow
from app.database.schemas import ChunkCreate, DocumentCreate


class PostgresDocumentRepository:
    """Schema preparation operations; caller owns the session transaction."""

    def __init__(self, session, embedding_dimensions):
        self.session, self.embedding_dimensions = session, embedding_dimensions

    async def add_document(self, document: DocumentCreate):
        row = TechnicalDocumentRow(**document.model_dump())
        self.session.add(row)
        await self.session.flush()
        return row.id

    async def add_chunk(self, chunk: ChunkCreate):
        chunk.validate_dimensions(self.embedding_dimensions)
        row = DocumentChunkRow(**chunk.model_dump())
        self.session.add(row)
        await self.session.flush()
        return row.id
