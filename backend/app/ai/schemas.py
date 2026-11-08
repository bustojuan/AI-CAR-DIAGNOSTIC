"""Schemas shared by structured LLM output and the public diagnostic contract."""

from app.models.diagnostic import Assessment, SymptomExtraction

__all__ = ["Assessment", "SymptomExtraction"]
