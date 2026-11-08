"""TEST HARNESS ONLY: real FastAPI over TCP, explicit memory store and fake model.

Never selected by application startup. No persistent/paid services are contacted.
"""

import os
import sys
from pathlib import Path

import uvicorn

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "backend"))

from app.core.config import Settings  # noqa: E402
from app.main import create_app  # noqa: E402
from app.repositories.memory import MemoryStore  # noqa: E402
from tests.conftest import FakeClient  # noqa: E402

if __name__ == "__main__":
    settings = Settings(_env_file=None, database_url=None, openai_api_key=None, mcp_enabled=False)
    uvicorn.run(
        create_app(settings, store=MemoryStore(), llm_client=FakeClient()),
        host="127.0.0.1",
        port=int(os.environ.get("MOTOR_E2E_BACKEND_PORT", "18001")),
        loop="app.core.event_loop:selector_loop",
        log_level="warning",
    )
