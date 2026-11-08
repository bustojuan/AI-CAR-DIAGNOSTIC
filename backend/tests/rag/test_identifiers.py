from app.core.config import Settings
from app.models.vehicle import seed_vehicle
from app.rag.identifiers import component_identifiers, contains_identifier
from app.rag.service import RagService
from tests.rag.fakes import FakeEmbeddings, FakeKnowledge
from tests.rag.test_service import metadata


def test_whole_component_and_obd_tags_are_distinct_from_vehicle_values():
    assert component_identifiers("g31/G310, SC2 J104 J500, P0401; 2009 CFFB 0A4") == [
        "G31",
        "G310",
        "SC2",
        "J104",
        "J500",
        "P0401",
    ]
    assert contains_identifier("pressure sensor -G31-", "G31")
    assert not contains_identifier("G310 connector", "G31")
    assert not contains_identifier("G31A connector", "G31")


def test_identifier_extraction_is_bounded():
    assert len(component_identifiers(" ".join(f"G{i}" for i in range(50)))) == 8


async def fixture_service():
    service = RagService(
        FakeKnowledge(),
        FakeEmbeddings(),
        Settings(_env_file=None, embedding_dimensions=4),
    )
    source = await service.ingest(
        "x.md",
        "text/markdown",
        b"Battery sensor G31 diagnostic reference.",
        metadata(),
    )
    await service.index(source.document_id)
    return service


async def test_unknown_identifier_returns_no_substitute_and_an_explicit_gap():
    result = await (await fixture_service()).retrieve(seed_vehicle(), "Battery sensor G9999?")
    assert result.available and not result.documents
    assert "G9999" in result.reason and "Do not substitute" in result.reason


async def test_partial_coverage_is_reported_and_model_context_cannot_add_identifiers():
    service = await fixture_service()
    result = await service.retrieve(seed_vehicle(), "Battery G31 and G42?", {"symptoms": "G247"})
    assert result.available and result.documents
    assert "No retrieved passage explicitly mentions: G42" in result.reason
    assert "G247" not in result.reason
