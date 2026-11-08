import socket
import threading
import time

import pytest
import uvicorn

from app.core.config import Settings
from app.mcp.server import create_http_app

TOKEN = "local-test-only-mcp-token-123456789"


@pytest.fixture(scope="module")
def mcp_http():
    # A real loopback TCP server, not ASGITransport or a mocked MCP protocol.
    settings = Settings(_env_file=None, automotive_provider="demo", mcp_token=TOKEN)
    sock = socket.socket()
    sock.bind(("127.0.0.1", 0))
    port = sock.getsockname()[1]
    server = uvicorn.Server(
        uvicorn.Config(
            create_http_app(settings),
            log_level="critical",
            loop="asyncio",
        )
    )
    thread = threading.Thread(target=server.run, kwargs={"sockets": [sock]}, daemon=True)
    thread.start()
    deadline = time.monotonic() + 15
    while not server.started and thread.is_alive() and time.monotonic() < deadline:
        time.sleep(0.01)
    assert server.started, "MCP HTTP server did not start"
    try:
        yield settings.model_copy(
            update={
                "mcp_enabled": True,
                "mcp_transport": "http",
                "mcp_http_url": f"http://127.0.0.1:{port}/mcp",
            }
        )
    finally:
        server.should_exit = True
        thread.join(timeout=15)
        sock.close()
        assert not thread.is_alive(), "MCP server failed to shut down"
