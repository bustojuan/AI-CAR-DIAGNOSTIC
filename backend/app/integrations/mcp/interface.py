from typing import Protocol

from app.mcp.schemas import AutomotiveResult
from app.models.common import Schema


class ToolResult(Schema):
    available: bool
    reason: str
    tools: list[str] = []
    provider: str = "unavailable"
    demo_data: bool = False


class ToolGateway(Protocol):
    async def status(self) -> ToolResult: ...
    async def execute(self, tool_name: str, arguments: dict) -> AutomotiveResult: ...


class UnavailableTools:
    async def status(self) -> ToolResult:
        return ToolResult(available=False, reason="External tools and catalogs are not connected.")

    async def execute(self, tool_name, arguments) -> AutomotiveResult:
        return AutomotiveResult(
            tool=tool_name,
            available=False,
            reason=(await self.status()).reason,
            provider="unavailable",
            demo_data=False,
            verification="unavailable",
        )
