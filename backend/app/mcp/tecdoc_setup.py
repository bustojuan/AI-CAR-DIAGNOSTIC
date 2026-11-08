"""Local TecDoc onboarding check. Does not contact or authenticate with TecAlliance."""

import argparse
import json

from pydantic import SecretStr, ValidationError
from pydantic_settings import BaseSettings, SettingsConfigDict

from app.models.vehicle import MVP_IDENTITY


class TecDocSetupSettings(BaseSettings):
    # Separate from runtime Settings: pending access must not change a working app,
    # require PostgreSQL/OpenAI, or become an enabled provider accidentally.
    model_config = SettingsConfigDict(
        env_file=".env", env_prefix="TECDOC_", extra="ignore", hide_input_in_errors=True
    )

    api_key: SecretStr | None = None
    provider_id: SecretStr | None = None
    endpoint: SecretStr | None = None


def setup_report(settings: TecDocSetupSettings) -> dict:
    """Report presence only; even complete configuration is not live verification."""
    configured = {}
    for name in type(settings).model_fields:
        value = getattr(settings, name)
        configured[f"TECDOC_{name.upper()}"] = bool(value and value.get_secret_value().strip())
    return {
        "provider": "tecdoc",
        "status": "pending_access_and_implementation",
        "network_requests_performed": False,
        "live_data_available": False,
        "adapter_implemented": False,
        "configuration_present": configured,
        "missing_configuration": [name for name, present in configured.items() if not present],
        "target_vehicle": {
            **MVP_IDENTITY,
            "identity_source": "owner_reported",
            "gearbox_code": None,
            "pr_codes": None,
            "tecdoc_vehicle_mapping_verified": False,
        },
        "pending_requirements": [
            "Obtain TecAlliance-authorized API access and assigned provider/client identifier.",
            "Obtain the assigned endpoint, authentication contract and API documentation.",
            "Confirm Spain coverage, quotas, cost and permitted use in this application.",
            "Confirm display and diagnostic-report snapshot retention rights.",
            "Verify the vehicle mapping; year and engine code alone do not prove fitment.",
            "Implement and test the adapter against the assigned API contract.",
            "Run an explicitly authorized live catalog query before enabling the provider.",
            "Confirm price type and availability; catalog prices are not merchant offers.",
        ],
        "reason": (
            "This is a local onboarding check, not a TecDoc connection test. "
            "No credentials, endpoint values, products, fitment or prices are returned. "
            "Use the explicitly labeled demo provider while access is pending."
        ),
    }


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--env-file", default=".env", help="Local configuration file to inspect")
    args = parser.parse_args(argv)
    try:
        result = setup_report(TecDocSetupSettings(_env_file=args.env_file))
    except (ValidationError, OSError, UnicodeError):
        # Never print exception text: configuration errors can contain credentials.
        print(json.dumps({"status": "invalid_local_configuration", "live_data_available": False}))
        return 2
    print(json.dumps(result, indent=2))
    # Never report connection success just because credential-shaped strings exist.
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
