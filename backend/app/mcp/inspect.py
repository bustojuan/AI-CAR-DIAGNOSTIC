"""Reproducible SDK-client discovery and invocation, independent of FastAPI/DB/LLM."""

import argparse
import asyncio

from app.core.config import Settings
from app.core.logging import configure_logging
from app.integrations.mcp.client import MCPGateway
from app.mcp.schemas import ToolVehicle
from app.models.vehicle import seed_vehicle


async def inspect_tools(action):
    settings = Settings()
    settings.mcp_enabled = True
    gateway = MCPGateway(settings)
    if action == "list":
        result = await gateway.status()
    elif action == "search":
        result = await gateway.execute(
            "search_parts",
            {
                "vehicle": seed_vehicle().model_dump(
                    mode="json", include=set(ToolVehicle.model_fields)
                ),
                "component": "glow plugs",
            },
        )
    elif action == "fitment":
        result = await gateway.execute(
            "check_compatibility",
            {
                "vehicle": seed_vehicle().model_dump(
                    mode="json", include=set(ToolVehicle.model_fields)
                ),
                "part_id": "DEMO-001",
            },
        )
    else:
        result = await gateway.execute("get_part_prices", {"part_id": "DEMO-001"})
    print(result.model_dump_json(indent=2))
    return 0 if result.available else 1


def main():
    configure_logging()
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("action", choices=["list", "search", "fitment", "prices"])
    args = parser.parse_args()
    raise SystemExit(asyncio.run(inspect_tools(args.action)))


if __name__ == "__main__":
    main()
