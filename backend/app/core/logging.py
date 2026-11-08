import logging
from contextvars import ContextVar

request_id_context = ContextVar("request_id", default="-")


def configure_logging() -> None:
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s %(message)s")
    # Provider/HTTP debug logs can contain payloads, so suppress them by default.
    for name in ("httpx", "httpcore", "httpx2", "httpcore2", "openai"):
        logging.getLogger(name).setLevel(logging.WARNING)
    # SDK validation/transport diagnostics may include untrusted input values.
    # Application-owned MCP telemetry records sanitized categories and identifiers instead.
    logging.getLogger("mcp").setLevel(logging.CRITICAL)
