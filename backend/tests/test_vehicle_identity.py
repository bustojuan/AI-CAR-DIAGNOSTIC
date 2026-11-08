from app.ai.prompts import COMMON
from app.models.vehicle import GOLF_ID, seed_vehicle
from app.rag.sources import DOCUMENTATION_TARGET


def test_confirmed_identity_is_shared_by_seed_registry_and_model_context(client, fake):
    vehicle = seed_vehicle()
    assert (vehicle.model_year, vehicle.engine_code) == (2009, "CFFB")
    assert DOCUMENTATION_TARGET["engine_code"] == "CFFB"
    assert DOCUMENTATION_TARGET["gearbox_code"] is None
    assert DOCUMENTATION_TARGET["pr_codes"] is None
    assert "2009 2.0 TDI" in COMMON and "unconfirmed" in COMMON
    response = client.post(
        "/api/v1/diagnostics",
        json={
            "vehicle_id": str(GOLF_ID),
            "description": "Difficult cold starting.",
        },
    )
    assert response.status_code == 201
    payload = fake.calls[-1][2]["vehicle"]
    assert payload["model_year"] == 2009 and payload["engine_code"] == "CFFB"


def test_mvp_guard_accepts_2009_and_rejects_legacy_2006_without_changing_history(client):
    before = client.get(f"/api/v1/vehicles/{GOLF_ID}").json()
    invalid = client.patch(f"/api/v1/vehicles/{GOLF_ID}", json={"model_year": 2006})
    assert invalid.status_code == 422
    assert client.get(f"/api/v1/vehicles/{GOLF_ID}").json() == before
    assert client.patch(f"/api/v1/vehicles/{GOLF_ID}", json={"model_year": 2009}).status_code == 200
