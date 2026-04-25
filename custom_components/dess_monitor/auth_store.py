"""HA-backed persistence for SDK auth tokens.

Adapter that plugs a Home Assistant ``Store`` into the SDK's
:class:`~custom_components.dess_monitor.sdk.TokenStorage` protocol so the
:class:`Session` can survive HA restarts without re-login.
"""
from __future__ import annotations

import logging
from dataclasses import asdict
from typing import Any

from homeassistant.core import HomeAssistant
from homeassistant.helpers.storage import Store

from custom_components.dess_monitor.sdk import Auth, TokenStorage

_LOGGER = logging.getLogger(__name__)

_STORAGE_VERSION = 1


class HomeAssistantTokenStorage(TokenStorage):
    """Persists an :class:`Auth` token in HA storage, scoped per config entry.

    Storage is keyed by ``entry_id``; ``username`` is stored alongside the auth so
    that a credential change on the same entry invalidates the cached token.
    """

    def __init__(self, hass: HomeAssistant, entry_id: str, username: str) -> None:
        self._username = username
        self._store: Store = Store(hass, _STORAGE_VERSION, f"dess_monitor.auth.{entry_id}")

    async def load(self) -> Auth | None:
        try:
            stored = await self._store.async_load()
        except Exception:
            _LOGGER.exception("Failed to load cached auth")
            return None
        if not isinstance(stored, dict) or stored.get("username") != self._username:
            return None
        raw: Any = stored.get("auth")
        if not isinstance(raw, dict):
            return None
        try:
            return Auth(
                token=raw["token"],
                secret=raw["secret"],
                expire=int(raw["expire"]),
                uid=raw["uid"],
                usr=raw["usr"],
                issued_at=int(raw["issued_at"]),
            )
        except (KeyError, TypeError, ValueError):
            _LOGGER.warning("Cached auth has unexpected shape — discarding")
            return None

    async def save(self, auth: Auth) -> None:
        try:
            await self._store.async_save({"username": self._username, "auth": asdict(auth)})
        except Exception:
            _LOGGER.exception("Failed to persist auth cache")

    async def clear(self) -> None:
        try:
            await self._store.async_remove()
        except Exception:
            _LOGGER.exception("Failed to clear auth cache")
