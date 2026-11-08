"""Run with python -m app.mcp.server --transport stdio|http."""

import argparse
import hmac
from typing import Annotated

from mcp.server.fastmcp import FastMCP
from mcp.types import ToolAnnotations
from pydantic import Field
from starlette.responses import JSONResponse

from app.core.config import Settings
from app.core.logging import configure_logging, request_id_context
from app.mcp.providers import provider_for
from app.mcp.schemas import (
    AutomotiveResult,
    CheckCompatibility,
    GetPartPrices,
    SearchParts,
)
from app.mcp.service import AutomotiveService

Correlation = Annotated[str, Field(pattern=r"^[A-Za-z0-9_-]{1,64}$")]


class BearerMiddleware:
    def __init__(self, app, token):
        self.app, self.token = app, token

    async def __call__(self, scope, receive, send):
        async def no_store(message):
            if message["type"] == "http.response.start":
                message["headers"] = [
                    (key, value)
                    for key, value in message.get("headers", [])
                    if key.lower() != b"cache-control"
                ] + [(b"cache-control", b"no-store")]
            await send(message)

        if scope["type"] == "http":
            value = dict(scope.get("headers", [])).get(b"authorization", b"")
            if not hmac.compare_digest(value, b"Bearer " + self.token.encode()):
                return await JSONResponse({"error": "unauthorized"}, status_code=401)(
                    scope, receive, no_store
                )
        return await self.app(scope, receive, no_store if scope["type"] == "http" else send)


def create_server(settings: Settings | None = None, *, provider=None):
    settings = settings or Settings()
    service = AutomotiveService(
        provider or provider_for(settings.automotive_provider, settings),
        settings.mcp_provider_timeout_seconds,
        settings.mcp_max_result_bytes,
    )
    server = FastMCP(
        "Automotive tools",
        host="127.0.0.1",
        port=8766,
        stateless_http=True,
        json_response=True,
        max_request_body_size=65536,
        instructions="Read-only automotive data. Synthetic records are never verified fitment.",
    )

    async def execute(name, input, request_id):
        token = request_id_context.set(request_id or "-")
        try:
            return await service.execute(name, input.model_dump(mode="json"))
        finally:
            request_id_context.reset(token)

    annotations = ToolAnnotations(
        readOnlyHint=True, destructiveHint=False, idempotentHint=True, openWorldHint=False
    )

    @server.tool(annotations=annotations)
    async def search_parts(
        input: SearchParts, request_id: Correlation | None = None
    ) -> AutomotiveResult:
        """Find candidate parts. Candidates do not confirm compatibility or replacement need."""
        return await execute("search_parts", input, request_id)

    @server.tool(annotations=annotations)
    async def check_compatibility(
        input: CheckCompatibility, request_id: Correlation | None = None
    ) -> AutomotiveResult:
        """Check verified fitment. Missing engine data never implies a confirmed fit."""
        return await execute("check_compatibility", input, request_id)

    @server.tool(annotations=annotations)
    async def get_part_prices(
        input: GetPartPrices, request_id: Correlation | None = None
    ) -> AutomotiveResult:
        """Look up identified part prices; synthetic samples are not market prices."""
        return await execute("get_part_prices", input, request_id)

    return server


def create_http_app(settings: Settings | None = None, *, provider=None):
    settings = settings or Settings()
    if not settings.mcp_token:
        raise ValueError("Set MCP_TOKEN (at least 24 characters) before starting HTTP")
    app = create_server(settings, provider=provider).streamable_http_app()
    app.add_middleware(BearerMiddleware, token=settings.mcp_token.get_secret_value())
    return app


def main():
    parser = argparse.ArgumentParser(description="Local automotive MCP server")
    parser.add_argument("--transport", choices=["stdio", "http"], default="stdio")
    args = parser.parse_args()
    configure_logging()
    settings = Settings(_env_file=None) if args.transport == "stdio" else Settings()
    if args.transport == "stdio":
        create_server(settings).run(transport="stdio")
    else:
        import uvicorn

        uvicorn.run(create_http_app(settings), host="127.0.0.1", port=8766)


if __name__ == "__main__":
    main()
