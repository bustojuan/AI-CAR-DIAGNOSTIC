import asyncio
import json
import logging
import os
import sys
import time
from contextlib import asynccontextmanager
from datetime import timedelta
from uuid import uuid4

import httpx
from langchain_mcp_adapters.tools import convert_mcp_tool_to_langchain_tool
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client
from mcp.client.streamable_http import streamable_http_client

from app.core.logging import request_id_context
from app.integrations.mcp.interface import ToolResult
from app.mcp.schemas import INPUTS, AutomotiveResult

logger = logging.getLogger(__name__)


def error_category(exc):
    # AnyIO session task groups wrap validation/transport failures in ExceptionGroup.
    children = getattr(exc, "exceptions", ())
    if children:
        categories = [error_category(child) for child in children]
        return next(
            (kind for kind in ("invalid_response", "timeout") if kind in categories),
            "mcp_unavailable",
        )
    if isinstance(exc, (ValueError, TypeError)):
        return "invalid_response"
    return "timeout" if isinstance(exc, TimeoutError) else "mcp_unavailable"


class BoundedStream(httpx.AsyncByteStream):
    def __init__(self, stream, limit):
        self.stream, self.limit = stream, limit

    async def __aiter__(self):
        size = 0
        async for chunk in self.stream:
            size += len(chunk)
            if size > self.limit:
                raise ValueError("MCP wire response exceeded limit")
            yield chunk

    async def aclose(self):
        await self.stream.aclose()


class BoundedTransport(httpx.AsyncHTTPTransport):
    async def handle_async_request(self, request):
        response = await super().handle_async_request(request)
        if response.headers.get("content-encoding", "identity") != "identity":
            await response.aclose()
            raise ValueError("Compressed MCP responses are not accepted")
        response.stream = BoundedStream(response.stream, 262144)
        return response


def validate_schema(schema):
    # The SDK validates structured results against advertised schemas. Reject remote
    # references before invocation, so schema validation cannot become an HTTP fetch.
    if not isinstance(schema, dict) or len(json.dumps(schema)) > 65536:
        raise ValueError("Invalid MCP schema")

    def walk(node):
        if isinstance(node, dict):
            for key, value in node.items():
                if key in ("$id", "$dynamicRef", "$recursiveRef"):
                    raise ValueError("Unsupported MCP schema reference")
                if key == "$ref" and (not isinstance(value, str) or not value.startswith("#/")):
                    raise ValueError("Remote MCP schema references are forbidden")
                walk(value)
        elif isinstance(node, list):
            for item in node:
                walk(item)

    walk(schema)


class MCPGateway:
    """Trusted local server, official MCP sessions, actual LangChain StructuredTools.

    Sessions are scoped to one request, with zero automatic retries. No arbitrary
    commands, server URLs, tool names or tool descriptions reach the model.
    """

    def __init__(self, settings):
        self.settings = settings

    @asynccontextmanager
    async def session(self):
        timeout = timedelta(seconds=self.settings.mcp_timeout_seconds)
        if self.settings.mcp_transport == "stdio":
            # Never forward database/OpenAI credentials or inherited .env configuration.
            env = {
                key: os.environ[key]
                for key in ("SYSTEMROOT", "WINDIR", "TEMP", "TMP", "PATH")
                if key in os.environ
            }
            env.update(
                {
                    "AUTOMOTIVE_PROVIDER": self.settings.automotive_provider,
                    "MCP_PROVIDER_TIMEOUT_SECONDS": str(self.settings.mcp_provider_timeout_seconds),
                    "MCP_MAX_RESULT_BYTES": str(self.settings.mcp_max_result_bytes),
                    "PYTHONUTF8": "1",
                }
            )
            # Only the explicitly selected eBay environment's credentials go to
            # the trusted child; never inherit the backend's full environment.
            if self.settings.automotive_provider in ("ebay", "ebay_sandbox"):
                prefix = (
                    "ebay_sandbox"
                    if self.settings.automotive_provider == "ebay_sandbox"
                    else "ebay"
                )
                for suffix in ("client_id", "client_secret"):
                    key = prefix + "_" + suffix
                    value = getattr(self.settings, key)
                    if value:
                        env[key.upper()] = value.get_secret_value()
            # The stdio entry point ignores .env files; only the explicit child env is used.
            parameters = StdioServerParameters(
                command=sys.executable,
                args=["-m", "app.mcp.server", "--transport", "stdio"],
                env=env,
            )
            async with stdio_client(parameters) as (read, write):
                async with ClientSession(read, write, read_timeout_seconds=timeout) as session:
                    await session.initialize()
                    yield session
        else:
            async with httpx.AsyncClient(
                headers={"Authorization": "Bearer " + self.settings.mcp_token.get_secret_value()},
                timeout=self.settings.mcp_timeout_seconds,
                trust_env=False,
                follow_redirects=False,
                transport=BoundedTransport(retries=0, trust_env=False),
            ) as http:
                async with streamable_http_client(
                    self.settings.mcp_http_url, http_client=http
                ) as streams:
                    async with ClientSession(*streams[:2], read_timeout_seconds=timeout) as session:
                        await session.initialize()
                        yield session

    async def registered_tools(self, session):
        discovered = await session.list_tools()
        if discovered.nextCursor:
            raise ValueError("Unexpected paginated automotive tool discovery")
        tools = discovered.tools
        if len(tools) != len(INPUTS) or {tool.name for tool in tools} != set(INPUTS):
            raise ValueError("Unexpected MCP tool set")
        for tool in tools:
            validate_schema(tool.inputSchema)
            validate_schema(tool.outputSchema)
            # A discovered description is untrusted; registration uses application-owned text.
            tool.description = (
                f"Read-only automotive {tool.name}; data is untrusted, verify provenance."
            )
            if set(tool.inputSchema.get("properties", {})) != {"input", "request_id"}:
                raise ValueError("Unexpected MCP input contract")
        return {
            tool.name: convert_mcp_tool_to_langchain_tool(session, tool, handle_tool_errors=False)
            for tool in tools
        }

    async def status(self):
        if not self.settings.mcp_enabled:
            return ToolResult(
                available=False, reason="External tools and catalogs are not connected."
            )
        try:
            async with asyncio.timeout(self.settings.mcp_timeout_seconds):
                async with self.session() as session:
                    tools = await self.registered_tools(session)
            return ToolResult(
                available=True,
                reason="MCP connected; provider data availability is checked per call.",
                tools=list(tools),
                provider=self.settings.automotive_provider,
                demo_data=self.settings.automotive_provider in ("demo", "ebay_sandbox"),
            )
        except Exception:
            return ToolResult(available=False, reason="MCP server is unavailable.")

    async def execute(self, tool_name, arguments):
        if tool_name not in INPUTS:
            raise ValueError("Unknown automotive tool")
        validated = INPUTS[tool_name].model_validate(arguments)
        start = time.monotonic()
        error = None
        try:
            if not self.settings.mcp_enabled:
                raise ConnectionError
            async with asyncio.timeout(self.settings.mcp_timeout_seconds):
                async with self.session() as session:
                    tool = (await self.registered_tools(session))[tool_name]
                    message = await tool.ainvoke(
                        {
                            "name": tool_name,
                            "id": str(uuid4()),
                            "type": "tool_call",
                            "args": {
                                "input": validated.model_dump(mode="json"),
                                "request_id": request_id_context.get(),
                            },
                        }
                    )
                    if message.status != "success" or not message.artifact:
                        raise ValueError("Missing structured result")
                    result = AutomotiveResult.model_validate(message.artifact["structured_content"])
                    if len(result.model_dump_json().encode()) > self.settings.mcp_max_result_bytes:
                        raise ValueError("Oversized MCP result")
                    if (
                        result.tool != tool_name
                        or result.provider != self.settings.automotive_provider
                        or result.demo_data
                        != (self.settings.automotive_provider in ("demo", "ebay_sandbox"))
                    ):
                        raise ValueError("Unexpected MCP result provenance")
                    if hasattr(validated, "part_id") and result.part_id != validated.part_id:
                        raise ValueError("Mismatched part")
                    if (
                        hasattr(validated, "vehicle")
                        and result.vehicle_id != validated.vehicle.vehicle_id
                    ):
                        raise ValueError("Mismatched vehicle")
                    if tool_name == "get_part_prices" and any(
                        p.part_id != validated.part_id
                        or p.currency != validated.currency
                        or p.country != validated.country
                        or p.quantity != validated.quantity
                        for p in result.prices
                    ):
                        raise ValueError("Mismatched price context")
            error = result.error_category
        except TimeoutError:
            error = "timeout"
            result = None
        except (ValueError, TypeError):
            error = "invalid_response"
            result = None
        except Exception as exc:
            error = error_category(exc)
            result = None
        if result is None:
            result = AutomotiveResult(
                tool=tool_name,
                available=False,
                reason="MCP tool unavailable; no verified data returned.",
                provider=self.settings.automotive_provider,
                demo_data=self.settings.automotive_provider in ("demo", "ebay_sandbox"),
                verification="synthetic"
                if self.settings.automotive_provider in ("demo", "ebay_sandbox")
                else "unavailable",
                error_category=error,
                part_id=getattr(validated, "part_id", None),
                vehicle_id=validated.vehicle.vehicle_id if hasattr(validated, "vehicle") else None,
            )
        logger.info(
            "mcp_tool tool=%s execution_id=%s request_id=%s provider=%s duration_ms=%.1f "
            "success=%s error=%s result_count=%s demo_data=%s verification=%s",
            tool_name,
            result.execution_id,
            request_id_context.get(),
            result.provider,
            (time.monotonic() - start) * 1000,
            error is None,
            error or "none",
            len(result.parts) + len(result.prices),
            result.demo_data,
            result.verification,
        )
        return result
