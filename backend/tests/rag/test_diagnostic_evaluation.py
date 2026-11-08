"""Evaluation must detect corrupted provenance without making paid provider calls."""

import hashlib
from copy import deepcopy
from uuid import uuid4

import pytest

from app.integrations.rag.interface import RetrievedDocument
from app.models.vehicle import seed_vehicle
from app.rag.diagnostic_evaluation import citation_checks, report_checks
from app.rag.schemas import SourceCitation


@pytest.fixture
def evidence():
    document_id, chunk_id = uuid4(), uuid4()
    text = "Authored fixture: a slow starter does not confirm a failed battery."
    metadata = {
        "id": document_id,
        "title": "Authored reference",
        "publisher": "Test publisher",
        "source_url": "https://example.org/reference",
        "public_source_url": False,
        "evidence_type": "third_party_technical",
        "verification_status": "verified",
        "license_status": "authorized",
        "ingestion_status": "processed",
        "manufacturer": "Volkswagen",
        "model": "Golf Plus",
        "model_year_start": 2009,
        "model_year_end": 2009,
        "engine": "2.0 TDI",
        "engine_code": "CFFB",
        "transmission": "Manual",
    }
    citation = SourceCitation(
        document_id=document_id,
        chunk_id=chunk_id,
        document_title=metadata["title"],
        publisher=metadata["publisher"],
        source_url=None,
        page=101,
        section="Starting",
        evidence_type="third_party_technical",
        verification_status="verified",
    )
    hit = RetrievedDocument(
        document_id=document_id,
        title=metadata["title"],
        source="Fixture",
        relevant_text=text,
        page=101,
        section="Starting",
        citation=citation,
    )
    chunks = [
        {
            "chunk_id": chunk_id,
            "text": text,
            "page": 101,
            "section": "Starting",
            "content_hash": hashlib.sha256(text.encode()).hexdigest(),
        }
    ]
    return citation, hit, metadata, chunks


def check(evidence):
    return citation_checks(*evidence, seed_vehicle(), False)


def test_complete_citation_metadata_and_text_match(evidence):
    assert all(check(evidence).values())


@pytest.mark.parametrize(
    "change",
    [
        {"document_title": "Invented title"},
        {"publisher": "Invented publisher"},
        {"page": 999},
        {"section": "Invented section"},
        {"document_id": uuid4()},
        {"source_url": "https://example.org/reference"},
        {"evidence_type": "official_manufacturer"},
        {"verification_status": "unverified"},
    ],
)
def test_metadata_tampering_including_private_url_is_detected(evidence, change):
    citation, hit, metadata, chunks = evidence
    altered = citation.model_copy(update=change)
    checks = check((altered, hit, metadata, chunks))
    assert not checks["citation_metadata_matches_storage"]


def test_unknown_chunk_is_not_a_valid_citation(evidence):
    citation, hit, metadata, chunks = evidence
    checks = check((citation.model_copy(update={"chunk_id": uuid4()}), hit, metadata, chunks))
    assert not all(checks.values())


def test_retrieved_text_and_stored_hash_are_checked_independently(evidence):
    citation, hit, metadata, chunks = evidence
    hit = hit.model_copy(update={"relevant_text": "Unsupported replacement advice."})
    chunks = deepcopy(chunks)
    chunks[0]["content_hash"] = "0" * 64
    checks = check((citation, hit, metadata, chunks))
    assert not checks["retrieved_text_matches_storage"]
    assert not checks["chunk_hash_matches_storage"]


@pytest.mark.parametrize(
    "change,key",
    [
        ({"license_status": "restricted"}, "source_eligible"),
        ({"verification_status": "unverified"}, "source_eligible"),
        ({"engine_code": "UNRELATED"}, "source_in_allowed_scope"),
        ({"model": "Passat"}, "source_in_allowed_scope"),
    ],
)
def test_permissions_and_vehicle_scope_are_separate_from_identity(evidence, change, key):
    citation, hit, metadata, chunks = evidence
    assert not check((citation, hit, {**metadata, **change}, chunks))[key]


def test_provider_error_cannot_be_counted_as_completed_evaluation():
    checks = report_checks({"expected_status": 201}, 503, {"error": {}}, [], [], None)
    assert not all(checks.values())


def test_empty_request_must_not_call_a_provider():
    case = {"expected_status": 422}
    assert all(report_checks(case, 422, {}, [], [], None).values())
    assert not all(report_checks(case, 422, {}, [{}], [], None).values())


def test_critical_report_must_bypass_providers_and_preserve_saved_report():
    case = {
        "expected_status": 201,
        "expected_mode": "deterministic_safety",
        "minimum_urgency": "critical",
    }
    report = {
        "generation_mode": "deterministic_safety",
        "urgency_level": "critical",
        "possible_causes": [],
        "citations": [],
        "driving_recommendation": "stop_safely_do_not_drive",
        "professional_assistance_recommended": True,
    }
    assert all(report_checks(case, 201, report, [], [], deepcopy(report)).values())
    assert not all(report_checks(case, 201, report, [{}], [], report).values())
    altered = {**report, "urgency_level": "low"}
    assert not all(report_checks(case, 201, report, [], [], altered).values())
