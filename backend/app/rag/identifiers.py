"""Exact component and OBD tags stated in a question; never inferred fitment."""

import re

CODE = re.compile(
    r"(?<![A-Za-z0-9])(?:(?:SC|SB|SA|G|J|N|F|E|K|V|T)\d{1,5}[a-z]?|[PBCU]\d{4})"
    r"(?![A-Za-z0-9])",
    re.IGNORECASE,
)


def component_identifiers(text):
    return list(dict.fromkeys(match.group().upper() for match in CODE.finditer(text)))[:8]


def identifier_pattern(identifier):
    return r"(^|[^A-Za-z0-9])" + re.escape(identifier) + r"([^A-Za-z0-9]|$)"


def contains_identifier(text, identifier):
    return bool(re.search(identifier_pattern(identifier), text, re.IGNORECASE))
