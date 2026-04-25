"""Self-discovering provider-key mapping for canonical metrics.

Public surface intentionally small — instantiate :class:`MappingDiscovery`
with a :class:`MappingStorage` and call ``resolve(device_pn, canonical, data)``
from the coordinator/sensor layer.
"""
from __future__ import annotations

from .discovery import MappingDiscovery
from .seed import (
    CANONICAL_METRICS,
    MATCH_FIELD_ID,
    MATCH_FIELD_PAR,
    SIGN_NEGATIVE,
    SIGN_POSITIVE,
    ProviderKeyCandidate,
)
from .storage import InMemoryMappingStorage, MappingStorage

__all__ = [
    "CANONICAL_METRICS",
    "InMemoryMappingStorage",
    "MATCH_FIELD_ID",
    "MATCH_FIELD_PAR",
    "MappingDiscovery",
    "MappingStorage",
    "ProviderKeyCandidate",
    "SIGN_NEGATIVE",
    "SIGN_POSITIVE",
]
