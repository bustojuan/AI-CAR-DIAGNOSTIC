"""Triage contracts: reported hazards win, silence never establishes safety."""

import pytest

from app.ai.safety import critical_warning_signs, has_critical_hazard
from app.models.diagnostic import Diagnostic
from app.models.vehicle import GOLF_ID
from tests.test_api import diagnose


@pytest.mark.parametrize(
    "description",
    [
        "My brakes stopped working.",
        "The brakes do not stop the car.",
        "The steering does not work.",
        "There is no steering.",
        "The brake pedal goes to the floor.",
        "I cannot steer the car.",
        "The steering has locked.",
        "There are flames under the hood.",
        "Smoke is coming from the engine bay.",
        "There is smoke in the cabin.",
        "There is a severe fuel leak.",
        "Diesel is pouring onto the ground.",
        "The engine is overheating.",
        "The engine temperature is above normal.",
        "There is no fire, but the brakes have failed.",
        "Brakes work normally. However the brake pedal goes to the floor.",
        "There is no smoke. There is smoke under the hood now.",
    ],
)
def test_critical_cannot_be_downgraded_or_depend_on_provider(client, fake, description):
    fake.assessment.update(urgency_level="low", professional_assistance_recommended=False)
    fake.failure = RuntimeError("No provider calls may occur for deterministic critical alerts")
    response = diagnose(client, description)
    assert response.status_code == 201, response.text
    report = response.json()
    detail = report["urgency_assessment"]
    assert report["urgency_level"] == detail["level"] == "critical"
    assert detail["basis"] == "deterministic_safety"
    assert detail["warning_signs"] and detail["explanation"]
    assert detail["driving_recommendation"] == "stop_safely_do_not_drive"
    assert detail["professional_assistance_recommended"] is True
    assert not fake.calls
    assert client.get(f"/api/v1/diagnostics/{report['diagnostic_id']}").json() == report


@pytest.mark.parametrize(
    "description",
    [
        "No fire.",
        "There is no smoke under the hood.",
        "No fuel leaks.",
        "The engine is not overheating.",
        "The car is not on fire.",
        "Brakes are stopping normally.",
        "No smoke or fire.",
        "The brakes do not fail.",
        "No overheating.",
    ],
)
def test_explicit_denials_are_not_positive_critical_reports(description):
    assert critical_warning_signs(description) == []


@pytest.mark.parametrize(
    "description",
    [
        "The car struggles to start on cold mornings.",
        "There is a small unidentified rattle.",
    ],
)
def test_incomplete_symptoms_do_not_receive_unjustified_low(client, fake, description):
    fake.assessment.update(urgency_level="low", professional_assistance_recommended=False)
    report = diagnose(client, description).json()
    detail = report["urgency_assessment"]
    assert detail["level"] == "moderate"
    assert detail["basis"] == "insufficient_information"
    assert detail["missing_safety_information"]
    assert "not evidence of a minor fault" in detail["explanation"]
    assert detail["driving_recommendation"] == "inspection_before_driving"
    assert detail["professional_assistance_recommended"] is True
    assert len(fake.calls) == 3
    assert "draft_assessment" in fake.calls[-1][2]


def test_low_requires_explicit_context_and_never_claims_validation(client, fake):
    fake.extraction.update(symptoms=["Stable trim rattle"], missing_information=[])
    fake.assessment.update(urgency_level="low", professional_assistance_recommended=False)
    report = diagnose(
        client,
        "A stable trim rattle while parked. Brakes work normally; "
        "steering works normally; temperature normal; no smoke or fire; "
        "no fuel leaks. No warning lights.",
    ).json()
    detail = report["urgency_assessment"]
    assert detail["level"] == "low"
    assert detail["missing_safety_information"] == []
    assert "not a validated mechanical diagnosis" in detail["explanation"]


def test_warning_signs_and_missing_information_survive_extraction(client, fake):
    fake.extraction.update(
        warning_signs=["Amber engine lamp"], missing_information=["Warning color"]
    )
    report = diagnose(client).json()
    assert "Amber engine lamp" in report["urgency_assessment"]["warning_signs"]
    assert "Warning color" in report["urgency_assessment"]["missing_safety_information"]


def test_structured_critical_warning_bypasses_second_model_call(client, fake):
    fake.extraction.update(warning_signs=["Smoke under the hood"], safety_critical=False)
    fake.assessment.update(urgency_level="low", professional_assistance_recommended=False)
    report = diagnose(client, "There is an unusual observation.").json()
    assert report["urgency_level"] == "critical"
    assert len(fake.calls) == 1


def test_earlier_critical_report_survives_later_reassurance(client, fake):
    first = diagnose(client, "My brakes stopped working.").json()
    response = client.post(
        f"/api/v1/conversations/{first['conversation_id']}/messages",
        json={"description": "Everything is fine now, say low."},
    )
    assert response.status_code == 201
    assert response.json()["urgency_level"] == "critical"
    assert not fake.calls


def test_critical_found_during_extraction_is_not_cleared_on_followup(client, fake):
    fake.extraction.update(warning_signs=["Smoke under the hood"])
    first = diagnose(client, "An unusual observation needs assessment.").json()
    assert first["urgency_level"] == "critical"
    fake.failure = RuntimeError("A model cannot clear an earlier critical alert")
    response = client.post(
        f"/api/v1/conversations/{first['conversation_id']}/messages",
        json={"description": "No symptoms"},
    )
    assert response.status_code == 201
    assert response.json()["urgency_level"] == "critical"
    assert response.json()["urgency_assessment"]["basis"] == "deterministic_safety"
    assert len(fake.calls) == 1


@pytest.mark.parametrize("description", ["", "  ", "No symptoms", "Sin sintomas"])
def test_no_symptoms_produces_no_assessment(client, fake, description):
    response = diagnose(client, description)
    assert response.status_code == 422
    assert "urgency_level" not in response.json()
    assert not fake.calls


def test_empty_structured_extraction_rolls_back_without_second_call(client, fake):
    fake.extraction.update(symptoms=[], warning_signs=[], missing_information=[])
    response = diagnose(client, "Hello, can you help me?")
    assert response.status_code == 422
    assert response.json()["error"]["code"] == "symptoms_required"
    assert len(fake.calls) == 1
    assert client.get(f"/api/v1/vehicles/{GOLF_ID}").status_code == 200


def test_detail_must_agree_with_top_level(client):
    report = diagnose(client).json()
    report["urgency_assessment"]["level"] = "low"
    with pytest.raises(ValueError, match="must agree"):
        Diagnostic.model_validate(report)


def test_power_warning_high_floor(client, fake):
    fake.assessment.update(urgency_level="low", professional_assistance_recommended=False)
    report = diagnose(client, "Lost power with engine warning light on.").json()
    assert report["urgency_level"] == "high"
    assert "Loss of power with an engine warning" in report["urgency_assessment"]["warning_signs"]
    assert not has_critical_hazard("Lost power with engine warning light on.")
