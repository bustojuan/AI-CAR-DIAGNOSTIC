from app.rag.sources import DOCUMENTATION_TARGET, PRIMARY_SOURCES, SOURCES


def test_registry_records_provenance_without_granting_remote_indexing_permission():
    assert DOCUMENTATION_TARGET["model_year"] == 2009
    assert DOCUMENTATION_TARGET["engine_code"] == "CFFB"
    required = {
        "source_name",
        "url",
        "publisher",
        "document_type",
        "applicable_vehicle",
        "applicable_engine",
        "verification_status",
        "license_status",
        "local_indexing_permission",
    }
    assert len({source["id"] for source in SOURCES}) == len(SOURCES)
    for source in SOURCES:
        assert required <= source.keys()
        assert source["automatically_indexed"] is False
        if source["id"] in PRIMARY_SOURCES:
            assert source["local_indexing_permission"] is False
            assert "unverified" in source["applicable_vehicle"]
