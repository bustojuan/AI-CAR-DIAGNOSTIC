import hmac
import json
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, File, Form, Header, Query, Request, UploadFile
from pydantic import ValidationError

from app.core.exceptions import AppError
from app.database.schemas import DocumentCreate
from app.rag.schemas import SearchRequest

router = APIRouter(tags=["RAG"])


def admin(request: Request, x_admin_token: Annotated[str | None, Header()] = None):
    expected = request.app.state.settings.rag_admin_token
    if not expected:
        raise AppError(
            503, "document_admin_disabled", "Configure RAG_ADMIN_TOKEN for document administration."
        )
    if not x_admin_token or not hmac.compare_digest(
        x_admin_token.encode(), expected.get_secret_value().encode()
    ):
        raise AppError(401, "admin_unauthorized", "Document administrator authentication required.")


def service(request: Request):
    if request.app.state.rag is None:
        raise AppError(503, "retrieval_not_configured", "PostgreSQL retrieval is not configured.")
    return request.app.state.rag


@router.post("/documents/upload", status_code=201, dependencies=[Depends(admin)])
async def upload(
    request: Request,
    metadata: Annotated[str, Form(max_length=16000)],
    file: Annotated[UploadFile, File()],
    source_page_start: Annotated[int, Form(ge=1, le=1000000)] = 1,
):
    rag = service(request)
    try:
        data = json.loads(metadata)
        if not isinstance(data, dict) or set(data) & {
            "content_hash",
            "storage_path",
            "ingestion_status",
            "extraction_error",
        }:
            raise ValueError
        validated = DocumentCreate.model_validate({**data, "content_hash": "0" * 64})
    except (ValueError, ValidationError):
        raise AppError(422, "invalid_document_metadata", "Invalid document metadata.") from None
    content = await file.read(request.app.state.settings.document_max_bytes + 1)
    try:
        return await rag.ingest(
            file.filename or "",
            file.content_type or "",
            content,
            validated,
            source_page_start=source_page_start,
        )
    finally:
        await file.close()


@router.get("/documents/sources", dependencies=[Depends(admin)])
async def sources():
    from app.rag.sources import SOURCES

    return SOURCES


@router.get("/documents", dependencies=[Depends(admin)])
async def documents(
    request: Request,
    limit: Annotated[int, Query(ge=1, le=100)] = 100,
    offset: Annotated[int, Query(ge=0)] = 0,
):
    return await service(request).knowledge.list(limit, offset)


@router.get("/documents/{document_id}", dependencies=[Depends(admin)])
async def document(document_id: UUID, request: Request):
    metadata, chunks = await service(request).knowledge.get(document_id)
    return {**metadata, "chunk_count": len(chunks)}


@router.delete("/documents/{document_id}", status_code=204, dependencies=[Depends(admin)])
async def delete_document(document_id: UUID, request: Request):
    await service(request).knowledge.delete(document_id)


@router.post("/documents/{document_id}/index", dependencies=[Depends(admin)])
async def index_document(document_id: UUID, request: Request):
    return await service(request).index(document_id)


@router.post("/retrieval/search")
async def search(data: SearchRequest, request: Request):
    vehicle = await request.app.state.vehicles.get(data.vehicle_id)
    return await service(request).retrieve(vehicle, data.query)


@router.get("/retrieval/status")
async def status(request: Request):
    settings = request.app.state.settings
    return {
        "enabled": settings.rag_enabled,
        "configured": request.app.state.rag is not None,
        "embeddings_configured": bool(settings.openai_api_key),
        "embedding_model": settings.embedding_model,
        "embedding_dimensions": settings.embedding_dimensions,
        "manufacturer_evidence": "Determined per retrieved source; never assumed.",
        "limitation": "Source licensing and applicability must be verified per document.",
    }


@router.get("/retrieval/stats", dependencies=[Depends(admin)])
async def stats(request: Request):
    return await service(request).knowledge.stats()
