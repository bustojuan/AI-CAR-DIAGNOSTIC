from uuid import uuid4

from app.models.vehicle import GOLF_ID
from tests.test_api import diagnose


def change(client, report, action="resolve", **extra):
    return client.post(
        f"/api/v1/conversations/{report['conversation_id']}/{action}",
        json={"expected_latest_diagnostic_id": report["diagnostic_id"], **extra},
    )


def urgency(client):
    response = client.get(f"/api/v1/vehicles/{GOLF_ID}/urgency")
    assert response.status_code == 200
    return response.json()


def cases(client, suffix=""):
    response = client.get(f"/api/v1/vehicles/{GOLF_ID}/cases{suffix}")
    assert response.status_code == 200
    return response.json()


def test_resolution_and_reopening_preserve_original_reports(client):
    report = diagnose(client, "My brakes stopped working.").json()
    assert cases(client)[0]["resolution_status"] == "active"
    resolved = change(client, report, resolution_note="Workshop visit completed.")
    assert resolved.status_code == 200, resolved.text
    case = resolved.json()
    assert case["resolution_status"] == "resolved" and case["resolved_at"]
    assert case["resolution_note"] == "Workshop visit completed."
    assert case["historical_urgency"] == "critical"
    stored = client.get(f"/api/v1/conversations/{report['conversation_id']}").json()
    assert stored["resolved_at"] == case["resolved_at"]
    assert stored["resolution_note"] == case["resolution_note"]
    assert urgency(client)["urgency_level"] is None
    assert client.get(f"/api/v1/diagnostics/{report['diagnostic_id']}").json() == report
    reopened = change(client, report, "reopen")
    assert reopened.status_code == 200
    assert reopened.json()["resolution_status"] == "active"
    assert reopened.json()["resolved_at"] is None
    assert reopened.json()["resolution_note"] is None
    assert urgency(client)["urgency_level"] == "critical"
    assert client.get(f"/api/v1/diagnostics/{report['diagnostic_id']}").json() == report


def test_aggregation_uses_highest_active_case_and_excludes_resolved(client, fake):
    assert urgency(client)["urgency_level"] is None
    moderate = diagnose(client).json()
    fake.assessment.update(urgency_level="high", driving_recommendation="inspection_before_driving")
    high = diagnose(client, "The starter now cranks slowly.").json()
    critical = diagnose(client, "The steering has failed.").json()
    assert urgency(client)["urgency_level"] == "critical"
    assert urgency(client)["active_case_count"] == 3
    assert change(client, critical).status_code == 200
    assert urgency(client)["urgency_level"] == "high"
    assert change(client, high).status_code == 200
    assert urgency(client)["urgency_level"] == "moderate"
    assert change(client, moderate).status_code == 200
    empty = urgency(client)
    assert empty["urgency_level"] is None and empty["active_case_count"] == 0
    assert empty["resolved_case_count"] == 3
    assert "does not independently establish" in empty["explanation"]
    assert len(cases(client, "?resolution_status=resolved")) == 3
    assert cases(client, "?resolution_status=active") == []
    assert len(cases(client)) == 3
    assert (
        client.get(f"/api/v1/vehicles/{GOLF_ID}/cases?resolution_status=unknown").status_code == 422
    )


def test_case_urgency_preserves_higher_earlier_assessment(client, fake):
    fake.assessment.update(urgency_level="high", driving_recommendation="inspection_before_driving")
    first = diagnose(client).json()
    fake.assessment.update(urgency_level="moderate")
    second = client.post(
        f"/api/v1/conversations/{first['conversation_id']}/messages",
        json={"description": "Starting is now a little easier."},
    ).json()
    assert second["urgency_level"] == "moderate"
    assert cases(client)[0]["assessment_count"] == 2
    assert cases(client)[0]["historical_urgency"] == "high"
    assert urgency(client)["urgency_level"] == "high"


def test_invalid_and_stale_transitions_are_rejected(client):
    report = diagnose(client).json()
    assert change(client, report, "reopen").status_code == 409
    latest = client.post(
        f"/api/v1/conversations/{report['conversation_id']}/messages",
        json={"description": "My brakes stopped working."},
    ).json()
    stale = change(client, report)
    assert stale.status_code == 409 and stale.json()["error"]["code"] == "stale_case"
    assert urgency(client)["urgency_level"] == "critical"
    assert change(client, latest, resolution_note="x" * 1001).status_code == 422
    assert change(client, latest, resolved_at="2020-01-01").status_code == 422
    assert change(client, latest).status_code == 200
    assert change(client, latest).status_code == 409
    assert change(client, {**report, "conversation_id": str(uuid4())}).status_code == 404


def test_resolved_case_becomes_active_on_new_critical_assessment(client, fake):
    report = diagnose(client).json()
    assert change(client, report).status_code == 200
    fake.failure = RuntimeError("New critical warning must bypass the model")
    response = client.post(
        f"/api/v1/conversations/{report['conversation_id']}/messages",
        json={"description": "There is smoke under the hood."},
    )
    assert response.status_code == 201
    assert response.json()["urgency_level"] == "critical"
    case = cases(client)[0]
    assert case["resolution_status"] == "active"
    assert case["resolved_at"] is None and case["resolution_note"] is None
    assert urgency(client)["urgency_level"] == "critical"
    assert change(client, report).status_code == 409


def test_empty_conversations_cannot_be_resolved_and_do_not_affect_urgency(client):
    created = client.post("/api/v1/conversations", json={"vehicle_id": str(GOLF_ID)}).json()
    empty = change(client, {**created, "diagnostic_id": str(uuid4())})
    assert empty.status_code == 409
    assert empty.json()["error"]["code"] == "case_not_assessed"
    assert cases(client) == []
    assert urgency(client)["urgency_level"] is None
    assert client.get(f"/api/v1/vehicles/{uuid4()}/urgency").status_code == 404
    assert client.get(f"/api/v1/vehicles/{uuid4()}/cases").status_code == 404
