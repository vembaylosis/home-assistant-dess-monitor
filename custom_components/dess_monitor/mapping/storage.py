"""Persistence interface for the per-device discovery cache.

Mirrors the pattern used in the SDK's :mod:`storage` module: a small
:class:`Protocol` plus an in-memory default. Real persistence (e.g. HA's
``Store``) is supplied by the integration via an adapter.
"""
from __future__ import annotations

from typing import Any, Protocol, runtime_checkable


@runtime_checkable
class MappingStorage(Protocol):
    """Pluggable persistence for the discovered key map.

    The payload is a JSON-serialisable dict produced by
    :meth:`MappingDiscovery.snapshot`. Implementations must accept any shape
    they previously produced; backward-incompat changes go through a
    ``version`` bump on the snapshot.
    """

    async def load(self) -> dict[str, Any] | None: ...

    async def save(self, data: dict[str, Any]) -> None: ...

    async def clear(self) -> None: ...


class InMemoryMappingStorage:
    """Default storage — process-local, lost on restart."""

    def __init__(self) -> None:
        self._data: dict[str, Any] | None = None

    async def load(self) -> dict[str, Any] | None:
        return self._data

    async def save(self, data: dict[str, Any]) -> None:
        self._data = data

    async def clear(self) -> None:
        self._data = None
