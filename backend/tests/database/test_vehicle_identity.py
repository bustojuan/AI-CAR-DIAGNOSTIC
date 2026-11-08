import httpx
import pytest
from sqlalchemy import text

from app.database.correct_vehicle_identity import correct
from app.main import create_app
from app.models.vehicle import GOLF_ID
from tests.conftest import FakeClient

pytestmark = pytest.mark.database


async def test_existing_vehicle_correction_preserves_history_and_survives_restart(db_settings):
    app = create_app(db_settings, llm_client=FakeClient())
    async with (
        app.router.lifespan_context(app),
        httpx.AsyncClient(transport=httpx.ASGITransport(app), base_url="http://test") as api,
    ):
        response = await api.post(
            "/api/v1/diagnostics",
            json={
                "vehicle_id": str(GOLF_ID),
                "description": "My brakes have failed.",
            },
        )
        assert response.status_code == 201
        report = response.json()
        resolved = await api.post(
            f"/api/v1/conversations/{report['conversation_id']}/resolve",
            json={"expected_latest_diagnostic_id": report["diagnostic_id"]},
        )
        assert resolved.status_code == 200
        async with app.state.store.sessions() as session, session.begin():
            await session.execute(
                text(
                    "UPDATE vehicles SET model_year=2006, engine_code=NULL, "
                    "mileage_km=183000, additional_information='Owner note retained' WHERE id=:id"
                ),
                {"id": GOLF_ID},
            )
    result = await correct(db_settings)
    assert result["before"] == {"model_year": 2006, "engine_code": None}
    assert result["after"] == {"model_year": 2009, "engine_code": "CFFB"}
    assert (await correct(db_settings))["before"] == result["after"]
    restarted = create_app(db_settings, llm_client=FakeClient())
    async with (
        restarted.router.lifespan_context(restarted),
        httpx.AsyncClient(transport=httpx.ASGITransport(restarted), base_url="http://test") as api,
    ):
        saved = (await api.get(f"/api/v1/vehicles/{GOLF_ID}")).json()
        assert saved["model_year"] == 2009 and saved["engine_code"] == "CFFB"
        assert saved["mileage_km"] == 183000
        assert saved["additional_information"] == "Owner note retained"
        assert (await api.get(f"/api/v1/diagnostics/{report['diagnostic_id']}")).json() == report
        case = (await api.get(f"/api/v1/conversations/{report['conversation_id']}")).json()
        assert case["resolution_status"] == "resolved" and case["diagnostic_ids"] == [
            report["diagnostic_id"]
        ]
