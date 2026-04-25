"""Self-discovering provider-key resolver.

Holds, for each ``(device_pn, canonical_name)`` pair, the candidate from
:mod:`.seed` that first matched live data. Subsequent ticks short-circuit to
that pinned candidate; when it stops matching (e.g. firmware change drops
the key), discovery re-runs and pins the new winner.

The cache is JSON-serialisable so it can be restored across HA restarts via
any :class:`MappingStorage` adapter — the integration plugs in an HA-backed
implementation; tests and standalone scripts use :class:`InMemoryMappingStorage`.
"""
from __future__ import annotations

import asyncio
import logging
from typing import Any, Optional, Union

from custom_components.dess_monitor.api.helpers import resolve_param, safe_float

from .seed import (
    CANONICAL_METRICS,
    MATCH_FIELD_PAR,
    SIGN_NEGATIVE,
    SIGN_POSITIVE,
    ProviderKeyCandidate,
)
from .storage import MappingStorage

_LOGGER = logging.getLogger(__name__)

_SNAPSHOT_VERSION = 1


class MappingDiscovery:
    """Per-config-entry resolver shared across all devices on the entry."""

    def __init__(self, storage: MappingStorage) -> None:
        self._storage = storage
        self._lock = asyncio.Lock()
        # (device_pn, canonical_name) -> winning candidate
        self._pinned: dict[tuple[str, str], ProviderKeyCandidate] = {}
        self._dirty = False
        self._loaded = False

    # --- lifecycle ----------------------------------------------------------

    async def async_load(self) -> None:
        async with self._lock:
            if self._loaded:
                return
            self._loaded = True
            try:
                stored = await self._storage.load()
            except Exception:
                _LOGGER.exception("Failed to load mapping cache")
                return
            if not isinstance(stored, dict):
                return
            if stored.get("version") != _SNAPSHOT_VERSION:
                return
            devices = stored.get("devices") or {}
            if not isinstance(devices, dict):
                return
            restored = 0
            for pn, metrics in devices.items():
                if not isinstance(metrics, dict):
                    continue
                for canonical, ref in metrics.items():
                    if not isinstance(ref, dict):
                        continue
                    cand = self._find_seed_candidate(
                        canonical,
                        ref.get("provider_key"),
                        ref.get("match_field"),
                    )
                    if cand is not None:
                        self._pinned[(pn, canonical)] = cand
                        restored += 1
            if restored:
                _LOGGER.debug("Restored %d pinned mappings from cache", restored)

    async def async_save(self) -> None:
        async with self._lock:
            if not self._dirty:
                return
            snapshot = self._snapshot_locked()
            self._dirty = False
        try:
            await self._storage.save(snapshot)
        except Exception:
            _LOGGER.exception("Failed to persist mapping cache")
            self._dirty = True  # retry next time

    async def async_clear(self) -> None:
        async with self._lock:
            self._pinned.clear()
            self._dirty = False
        try:
            await self._storage.clear()
        except Exception:
            _LOGGER.exception("Failed to clear mapping cache")

    # --- public API ---------------------------------------------------------

    @property
    def is_dirty(self) -> bool:
        return self._dirty

    def resolve(
            self,
            device_pn: str,
            canonical_name: str,
            data: dict[str, Any],
    ) -> Optional[Union[float, str]]:
        """Return the normalised value for ``canonical_name`` on ``device_pn``.

        ``None`` means the metric isn't present in ``data`` for any known
        provider key. Numeric values come back as ``float`` (already
        unit-normalised to W/V/A/Hz/°C/%); enum-typed values come back as the
        mapped string.
        """
        pinned = self._pinned.get((device_pn, canonical_name))
        if pinned is not None:
            value = self._extract(pinned, data)
            if value is not None:
                return value
            # pinned candidate stopped matching — fall through to re-discover
            self._pinned.pop((device_pn, canonical_name), None)
            self._dirty = True

        for candidate in CANONICAL_METRICS.get(canonical_name, ()):
            value = self._extract(candidate, data)
            if value is None:
                continue
            self._pinned[(device_pn, canonical_name)] = candidate
            self._dirty = True
            _LOGGER.debug(
                "Discovered mapping for %s on %s -> %s/%s",
                canonical_name, device_pn, candidate.match_field, candidate.provider_key,
            )
            return value
        return None

    def discovered_provider_key(
            self, device_pn: str, canonical_name: str,
    ) -> Optional[ProviderKeyCandidate]:
        """Inspect the pinned candidate for diagnostics. Read-only."""
        return self._pinned.get((device_pn, canonical_name))

    # --- internals ----------------------------------------------------------

    def _snapshot_locked(self) -> dict[str, Any]:
        devices: dict[str, dict[str, dict[str, str]]] = {}
        for (pn, canonical), cand in self._pinned.items():
            devices.setdefault(pn, {})[canonical] = {
                "provider_key": cand.provider_key,
                "match_field": cand.match_field,
            }
        return {"version": _SNAPSHOT_VERSION, "devices": devices}

    @staticmethod
    def _find_seed_candidate(
            canonical: Any, provider_key: Any, match_field: Any,
    ) -> Optional[ProviderKeyCandidate]:
        if not isinstance(canonical, str) or not isinstance(provider_key, str):
            return None
        if match_field not in ("id", "par"):
            return None
        for c in CANONICAL_METRICS.get(canonical, ()):
            if c.provider_key == provider_key and c.match_field == match_field:
                return c
        return None

    @staticmethod
    def _extract(
            cand: ProviderKeyCandidate, data: dict[str, Any],
    ) -> Optional[Union[float, str]]:
        item = MappingDiscovery._lookup_item(cand, data)
        if item is None:
            return None
        raw_val = item.get("val")
        if raw_val is None:
            return None
        if cand.value_map is not None:
            raw_str = raw_val if isinstance(raw_val, str) else str(raw_val)
            return cand.value_map.get(raw_str.lower())
        val = safe_float(raw_val, default=None)
        if val is None:
            return None
        unit = item.get("unit")
        if isinstance(unit, str) and unit == "kW":
            val *= 1000.0
        val = val * cand.scale + cand.offset
        if cand.sign == SIGN_POSITIVE:
            return val if val > 0 else 0.0
        if cand.sign == SIGN_NEGATIVE:
            return abs(val) if val < 0 else 0.0
        return val

    @staticmethod
    def _lookup_item(
            cand: ProviderKeyCandidate, data: dict[str, Any],
    ) -> Optional[dict[str, Any]]:
        """Return the matching payload item, preferring fresh WS data.

        Each device entry contains both polled subtrees (``last_data``,
        ``pars``, ``energy_flow``) and a live ``ws_data`` subtree fed by the
        WebSocket stream. We search ``ws_data`` first so that whenever the
        stream is delivering, its values shadow the (possibly minutes-old)
        polled snapshot — otherwise ``resolve_param`` would just return the
        first match it bumps into during a recursive walk, which is whatever
        landed earlier in dict-insertion order.

        Within each haystack we still try the declared ``match_field`` first
        and fall back to the opposite shape — devices often mirror the same
        key as ``id`` (``last_data``) and ``par`` (``pars`` envelope) at once,
        and the polled ``par`` form may carry ``status == 0`` (offline) when
        the ``id`` form has the live value.
        """
        if not isinstance(data, dict):
            return None

        for haystack in MappingDiscovery._iter_haystacks(data):
            item = MappingDiscovery._search_haystack(cand, haystack)
            if item is not None:
                return item
        return None

    @staticmethod
    def _iter_haystacks(data: dict[str, Any]):
        """Yield ``ws_data`` first (live), then the polled subtrees as a whole."""
        ws = data.get("ws_data")
        if isinstance(ws, dict) and ws:
            yield ws
        polled = {k: v for k, v in data.items() if k != "ws_data"}
        if polled:
            yield polled

    @staticmethod
    def _search_haystack(
            cand: ProviderKeyCandidate, haystack: dict[str, Any],
    ) -> Optional[dict[str, Any]]:
        primary_field = cand.match_field
        primary = resolve_param(
            haystack, {primary_field: cand.provider_key}, case_insensitive=True,
        )
        if isinstance(primary, dict):
            if not (primary_field == MATCH_FIELD_PAR and primary.get("status") == 0):
                return primary
        opposite_field = "id" if primary_field == MATCH_FIELD_PAR else "par"
        secondary = resolve_param(
            haystack, {opposite_field: cand.provider_key}, case_insensitive=True,
        )
        if not isinstance(secondary, dict):
            return None
        if opposite_field == MATCH_FIELD_PAR and secondary.get("status") == 0:
            return None
        return secondary
