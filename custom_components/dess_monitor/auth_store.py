"""Shared, persistent auth token store for the dess_monitor integration.

Avoids running ``auth_user`` simultaneously from both coordinators (rate-limited
by the upstream API) and survives Home Assistant restarts so that an existing
non-expired token is reused instead of re-authenticating.
"""
from __future__ import annotations

import asyncio
import logging
from datetime import datetime
from typing import Any

from homeassistant.core import HomeAssistant
from homeassistant.helpers.storage import Store

from custom_components.dess_monitor.api import auth_user

_LOGGER = logging.getLogger(__name__)

_STORAGE_VERSION = 1
_REFRESH_MARGIN_SECONDS = 3600


class AuthStore:
    """Per-config-entry auth token holder with persistent cache."""

    def __init__(self, hass: HomeAssistant, entry_id: str, username: str, password_hash: str) -> None:
        self._hass = hass
        self._username = username
        self._password_hash = password_hash
        self._lock = asyncio.Lock()
        self._auth: dict[str, Any] | None = None
        self._issued_at: int | None = None
        self._store: Store = Store(hass, _STORAGE_VERSION, f"dess_monitor.auth.{entry_id}")
        self._loaded = False

    async def _load_persisted(self) -> None:
        if self._loaded:
            return
        self._loaded = True
        try:
            stored = await self._store.async_load()
        except Exception:
            _LOGGER.exception("Failed to load cached auth")
            return
        if not stored:
            return
        if stored.get("username") != self._username:
            return
        self._auth = stored.get("auth")
        self._issued_at = stored.get("issued_at")
        _LOGGER.debug("Loaded cached auth, issued_at=%s", self._issued_at)

    async def _persist(self) -> None:
        try:
            await self._store.async_save({
                "username": self._username,
                "auth": self._auth,
                "issued_at": self._issued_at,
            })
        except Exception:
            _LOGGER.exception("Failed to persist auth cache")

    async def async_clear(self) -> None:
        async with self._lock:
            self._auth = None
            self._issued_at = None
            try:
                await self._store.async_remove()
            except Exception:
                _LOGGER.exception("Failed to clear auth cache")

    def _is_valid(self) -> bool:
        if self._auth is None or self._issued_at is None:
            return False
        expire = self._auth.get("expire")
        if not isinstance(expire, (int, float)):
            return False
        now = int(datetime.now().timestamp())
        return now < (self._issued_at + expire - _REFRESH_MARGIN_SECONDS)

    async def async_get(self, force_refresh: bool = False) -> dict[str, Any]:
        async with self._lock:
            await self._load_persisted()
            if not force_refresh and self._is_valid():
                return self._auth
            auth = await auth_user(self._username, self._password_hash)
            self._auth = auth
            self._issued_at = int(datetime.now().timestamp())
            await self._persist()
            return self._auth
