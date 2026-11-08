from unittest.mock import AsyncMock
from uuid import uuid4

import pytest

from app.core.config import Settings
from app.core.exceptions import AppError
from app.rag import index_pending


async def test_planning_never_constructs_an_embedding_client_even_with_a_key(monkeypatch):
    plan = {"document_ids": [str(uuid4())], "pending_chunks": 3}
    monkeypatch.setattr(
        index_pending,
        "audit_database",
        AsyncMock(
            return_value={
                "index_plan": plan,
                "blocked_documents": 2,
            }
        ),
    )

    def forbidden(*args):
        raise AssertionError("Planning must not construct paid services")

    monkeypatch.setattr(index_pending, "OpenAIEmbeddingClient", forbidden)
    monkeypatch.setattr(index_pending, "PostgresStore", forbidden)
    result = await index_pending.run(Settings(_env_file=None, openai_api_key="test-key"))
    assert result["mode"] == "plan_only" and result["results"] == []
    assert result["plan"] == plan and result["blocked_documents"] == 2


async def test_execute_without_credentials_fails_before_constructing_paid_services(monkeypatch):
    monkeypatch.setattr(
        index_pending,
        "audit_database",
        AsyncMock(
            return_value={
                "index_plan": {"document_ids": [str(uuid4())]},
                "blocked_documents": 0,
            }
        ),
    )
    with pytest.raises(AppError) as caught:
        await index_pending.run(Settings(_env_file=None), execute=True)
    assert caught.value.code == "embeddings_not_configured"


async def test_explicit_execution_stops_on_failure_and_keeps_completed_documents(monkeypatch):
    identifiers = [str(uuid4()) for _ in range(3)]
    monkeypatch.setattr(
        index_pending,
        "audit_database",
        AsyncMock(
            return_value={
                "index_plan": {"document_ids": identifiers},
                "blocked_documents": 5,
            }
        ),
    )
    store = type("Store", (), {"initialize": AsyncMock(), "close": AsyncMock()})()
    index = AsyncMock(side_effect=[{"indexed_chunks": 2}, AppError(503, "offline", "Offline")])
    monkeypatch.setattr(index_pending, "PostgresStore", lambda settings: store)
    monkeypatch.setattr(index_pending, "PostgresKnowledgeStore", lambda store: object())
    monkeypatch.setattr(index_pending, "OpenAIEmbeddingClient", lambda settings: object())
    monkeypatch.setattr(
        index_pending, "RagService", lambda *args: type("Rag", (), {"index": index})()
    )
    result = await index_pending.run(
        Settings(_env_file=None, openai_api_key="test-key"), execute=True
    )
    assert [row["status"] for row in result["results"]] == ["indexed", "failed"]
    assert index.await_count == 2
    store.close.assert_awaited_once()
