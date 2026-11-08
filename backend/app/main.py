from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from sqlalchemy.exc import SQLAlchemyError
from starlette.exceptions import HTTPException

from app.ai.diagnostic_agent import DiagnosticAgent
from app.ai.llm_client import LangChainClient, StructuredClient
from app.api.routes import conversations, diagnostics, health, parts, rag, vehicles
from app.core.config import Settings
from app.core.exceptions import AppError
from app.core.logging import configure_logging
from app.core.middleware import RequestMiddleware
from app.integrations.mcp.client import MCPGateway
from app.integrations.rag.interface import UnavailableRetriever
from app.rag.embeddings import OpenAIEmbeddingClient
from app.rag.repository import PostgresKnowledgeStore
from app.rag.service import RagService
from app.repositories.interfaces import Store
from app.repositories.postgres import PostgresStore
from app.services.conversation_service import ConversationService
from app.services.diagnostic_service import DiagnosticService
from app.services.vehicle_service import VehicleService


def create_app(
    settings: Settings | None = None,
    *,
    store: Store | None = None,
    llm_client: StructuredClient | None = None,
    knowledge_store=None,
    embedding_client=None,
    retriever=None,
    tools=None,
) -> FastAPI:
    configure_logging()
    settings = settings or Settings()
    store = store or PostgresStore(settings)
    if knowledge_store is None and isinstance(store, PostgresStore):
        knowledge_store = PostgresKnowledgeStore(store)
    rag_service = (
        RagService(knowledge_store, embedding_client or OpenAIEmbeddingClient(settings), settings)
        if knowledge_store is not None
        else None
    )
    retriever = retriever or (
        rag_service if settings.rag_enabled and rag_service else UnavailableRetriever()
    )

    @asynccontextmanager
    async def lifespan(app):
        await store.initialize()
        try:
            yield
        finally:
            await store.close()

    app = FastAPI(
        title="AI Car Diagnostic Assistant",
        version="0.4.0",
        description="Phase 4. PostgreSQL retrieval and automotive MCP. "
        "Hypotheses require professional verification. Local use only.",
        lifespan=lifespan,
    )
    app.state.settings = settings
    app.state.store = store
    app.state.rag = rag_service
    app.state.retriever = retriever
    app.state.tools = tools or MCPGateway(settings)
    app.state.vehicles = VehicleService(store)
    app.state.conversations = ConversationService(store)
    app.state.diagnostics = DiagnosticService(
        store,
        DiagnosticAgent(llm_client or LangChainClient(settings)),
        settings,
        retriever,
        app.state.tools,
    )

    def error(request: Request, status: int, code: str, message: str, details=None):
        data = {
            "code": code,
            "message": message,
            "request_id": getattr(request.state, "request_id", None),
        }
        if details is not None:
            data["details"] = details
        return JSONResponse(
            status_code=status,
            content={"error": data},
            headers={"X-Request-ID": data["request_id"] or "unknown"},
        )

    @app.exception_handler(AppError)
    async def application_error(request, exc):
        return error(request, exc.status, exc.code, exc.message)

    @app.exception_handler(RequestValidationError)
    async def validation_error(request, exc):
        # Do not echo sensitive input values or custom exception context.
        details = [{"location": list(item["loc"]), "type": item["type"]} for item in exc.errors()]
        return error(request, 422, "validation_error", "Request validation failed.", details)

    @app.exception_handler(HTTPException)
    async def http_error(request, exc):
        return error(request, exc.status_code, "http_error", "Request could not be processed.")

    @app.exception_handler(SQLAlchemyError)
    async def storage_error(request, exc):
        return error(request, 503, "database_unavailable", "PostgreSQL is unavailable.")

    for router in (
        health.router,
        vehicles.router,
        conversations.router,
        diagnostics.router,
        rag.router,
        parts.router,
    ):
        app.include_router(router, prefix="/api/v1")
    app.add_middleware(
        RequestMiddleware,
        max_bytes=settings.max_request_bytes,
        upload_max_bytes=settings.document_max_bytes + 65536,
        admin_token=settings.rag_admin_token.get_secret_value()
        if settings.rag_admin_token
        else None,
    )
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_methods=["GET", "POST", "PATCH", "DELETE"],
        allow_headers=["Content-Type", "X-Request-ID", "X-Admin-Token"],
        expose_headers=["X-Request-ID"],
    )
    return app


app = create_app()
