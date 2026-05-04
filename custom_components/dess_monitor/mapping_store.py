"""HA-backed persistence for the mapping discovery cache.

Adapter that plugs a Home Assistant ``Store`` into the mapping package's
:class:`~custom_components.dess_monitor.mapping.MappingStorage` protocol so
the discovered key map survives HA restarts.
"""
from __future__ import annotations

import logging
from typing import Any

from homeassistant.core import HomeAssistant
from homeassistant.helpers.storage import Store

from custom_components.dess_monitor.mapping import MappingStorage

_LOGGER = logging.getLogger(__name__)

_STORAGE_VERSION = 1


class HomeAssistantMappingStorage(MappingStorage):
    """Persists the mapping snapshot in HA storage, scoped per config entry."""

    def __init__(self, hass: HomeAssistant, entry_id: str) -> None:
        self._store: Store = Store(hass, _STORAGE_VERSION, f"dess_monitor.mapping.{entry_id}")

    async def load(self) -> dict[str, Any] | None:
        try:
            stored = await self._store.async_load()
        except Exception:
            _LOGGER.exception("Failed to load mapping cache")
            return None
        if not isinstance(stored, dict):
            return None
        return stored

    async def save(self, data: dict[str, Any]) -> None:
        try:
            await self._store.async_save(data)
        except Exception:
            _LOGGER.exception("Failed to persist mapping cache")

    async def clear(self) -> None:
        try:
            await self._store.async_remove()
        except Exception:
            _LOGGER.exception("Failed to clear mapping cache")
