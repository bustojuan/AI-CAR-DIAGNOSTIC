import asyncio
import logging
import time
from uuid import uuid4

from app.core.logging import request_id_context
from app.mcp.schemas import INPUTS, AutomotiveResult

logger = logging.getLogger(__name__)


class AutomotiveService:
    """Only shared provider boundary: bounded, schema checked, sanitized failures."""

    def __init__(self, provider, timeout=5.0, max_bytes=32768):
        self.provider, self.timeout, self.max_bytes = provider, timeout, max_bytes

    async def execute(self, tool: str, arguments: dict) -> AutomotiveResult:
        if tool not in INPUTS:
            raise ValueError("Unknown automotive tool")
        args = INPUTS[tool].model_validate(arguments)
        execution_id, start, error = uuid4(), time.monotonic(), None
        try:
            async with asyncio.timeout(self.timeout):
                raw = await self.provider.execute(tool, args)
            # Revalidation is essential even for mutated Pydantic objects returned by adapters.
            payload = raw.model_dump(mode="json") if isinstance(raw, AutomotiveResult) else raw
            result = AutomotiveResult.model_validate(payload)
            if len(result.model_dump_json().encode()) > self.max_bytes:
                raise ValueError("Oversized provider output")
            if result.provider != self.provider.name or result.demo_data != self.provider.demo_data:
                raise ValueError("Provider provenance mismatch")
            if result.tool != tool:
                raise ValueError("Tool result mismatch")
            if hasattr(args, "part_id") and result.part_id != args.part_id:
                raise ValueError("Part identifier mismatch")
            if hasattr(args, "vehicle") and result.vehicle_id != args.vehicle.vehicle_id:
                raise ValueError("Vehicle identifier mismatch")
            if tool == "search_parts":
                result.parts = list({p.part_id: p for p in result.parts}.values())[: args.limit]
            if tool == "get_part_prices" and any(
                p.part_id != args.part_id
                or p.country != args.country
                or p.currency != args.currency
                or p.quantity != args.quantity
                for p in result.prices
            ):
                raise ValueError("Price context mismatch")
        except TimeoutError:
            error = "timeout"
        except (ValueError, TypeError):
            error = "invalid_response"
        except Exception:
            error = "provider_failure"
        if error:
            result = AutomotiveResult(
                tool=tool,
                available=False,
                provider=self.provider.name,
                demo_data=self.provider.demo_data,
                verification="synthetic" if self.provider.demo_data else "unavailable",
                reason="Automotive provider could not return a validated result.",
                error_category=error,
                part_id=getattr(args, "part_id", None),
                vehicle_id=args.vehicle.vehicle_id if hasattr(args, "vehicle") else None,
            )
        # Adapters can return a sanitized failure instead of raising. Preserve its
        # reason while reporting the actual outcome in application telemetry.
        error = error or result.error_category
        result.execution_id = execution_id
        logger.info(
            "automotive_tool tool=%s execution_id=%s request_id=%s provider=%s duration_ms=%.1f "
            "success=%s error=%s result_count=%s demo_data=%s verification=%s",
            tool,
            execution_id,
            request_id_context.get(),
            self.provider.name,
            (time.monotonic() - start) * 1000,
            error is None,
            error or "none",
            len(result.parts) + len(result.prices),
            result.demo_data,
            result.verification,
        )
        return result
