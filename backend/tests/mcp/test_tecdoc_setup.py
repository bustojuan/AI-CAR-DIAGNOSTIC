"""Onboarding must not expose credentials, make requests, or enable a fake live provider."""

import json
import socket

import pytest

from app.core.config import Settings
from app.mcp.providers import provider_for
from app.mcp.tecdoc_setup import TecDocSetupSettings, main, setup_report


@pytest.fixture(autouse=True)
def isolated_tecdoc_environment(monkeypatch):
    for name in ("TECDOC_API_KEY", "TECDOC_PROVIDER_ID", "TECDOC_ENDPOINT"):
        monkeypatch.delenv(name, raising=False)


def test_pending_access_does_not_require_database_openai_or_make_network_calls(
    tmp_path, monkeypatch
):
    def forbidden(*args, **kwargs):
        raise AssertionError("Local onboarding must not make a network connection")

    monkeypatch.setattr(socket, "create_connection", forbidden)
    monkeypatch.setattr(socket.socket, "connect", forbidden)
    monkeypatch.chdir(tmp_path)
    report = setup_report(TecDocSetupSettings(_env_file=None))
    assert set(report["missing_configuration"]) == {
        "TECDOC_API_KEY",
        "TECDOC_PROVIDER_ID",
        "TECDOC_ENDPOINT",
    }
    assert report["target_vehicle"]["model_year"] == 2009
    assert report["target_vehicle"]["engine_code"] == "CFFB"
    assert report["target_vehicle"]["gearbox_code"] is None
    assert report["target_vehicle"]["pr_codes"] is None
    assert main([]) == 1


def test_configured_secrets_are_redacted_and_never_imply_live_access(tmp_path, capsys):
    values = {
        "TECDOC_API_KEY": "secret-test-key-not-real",
        "TECDOC_PROVIDER_ID": "private-test-provider-not-real",
        "TECDOC_ENDPOINT": "https://example.com/private-assigned-endpoint",
    }
    env_file = tmp_path / ".env"
    env_file.write_text(
        "\n".join(f"{key}={value}" for key, value in values.items()), encoding="utf-8"
    )
    assert main(["--env-file", str(env_file)]) == 1
    output = capsys.readouterr().out
    report = json.loads(output)
    assert all(report["configuration_present"].values())
    assert report["missing_configuration"] == []
    assert not report["live_data_available"] and not report["adapter_implemented"]
    assert report["status"] == "pending_access_and_implementation"
    assert not report["target_vehicle"]["tecdoc_vehicle_mapping_verified"]
    assert not report["network_requests_performed"]
    for value in values.values():
        assert value not in output
        assert value not in repr(TecDocSetupSettings(_env_file=env_file))


def test_preparation_cannot_select_an_unimplemented_provider():
    from pydantic import ValidationError

    with pytest.raises(ValidationError):
        Settings(_env_file=None, automotive_provider="tecdoc")
    with pytest.raises(ValueError):
        provider_for("tecdoc")


def test_bad_configuration_does_not_print_file_contents_or_error_details(tmp_path, capsys):
    invalid = tmp_path / ".env"
    invalid.write_bytes(b"TECDOC_API_KEY=secret-not-to-print\xff")
    assert main(["--env-file", str(invalid)]) == 2
    output = capsys.readouterr().out
    assert json.loads(output)["status"] == "invalid_local_configuration"
    assert "secret-not-to-print" not in output
