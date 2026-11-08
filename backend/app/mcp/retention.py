"""eBay results belong to transient Parts queries, never saved diagnostic reports."""

from app.core.exceptions import AppError

TRANSIENT_PROVIDERS = frozenset({"ebay", "ebay_sandbox"})


def require_persistable_report(diagnostic):
    if any(result.provider in TRANSIENT_PROVIDERS for result in diagnostic.tool_results):
        raise AppError(
            422,
            "transient_offer_not_persistable",
            "eBay offers can only be viewed temporarily in Parts, not saved in a diagnosis.",
        )
