"""Per-config-entry orchestrator for the SDK's :class:`DeviceStream`.

Spawns one WebSocket telemetry stream per active inverter, parses the frames
the upstream pushes, and folds the payload into the :class:`MainCoordinator`
``data`` snapshot so every existing sensor — without modification — sees the
fresh values via its mapping resolver.

The merge target is a dedicated ``ws_data`` subtree on the device entry, NOT
the polled ``last_data`` / ``pars`` / ``energy_flow``. Reasons:

- :class:`MappingDiscovery` walks the entire device dict recursively, so any
  ``id`` / ``par`` matched key is found regardless of which subtree it lives
  in. The seed needs no awareness of the WS shape.
- Polled snapshots stay deterministic — if the WS payload disagrees with what
  the cloud reports for the same key, the polled value still ground-truths
  whichever subtree appears first in iteration order, but the recursive walk
  finds either.
- Wiping ``ws_data`` on disconnect is trivial.

Coordinator updates are debounced: telemetry typically bursts a few frames
within ~half a second after a real change, and pushing every one of them to
~30 entities is wasteful.
"""
from __future__ import annotations

import asyncio
import logging
import time
from typing import Any

from homeassistant.core import HomeAssistant, callback

from custom_components.dess_monitor.const import WEBSOCKET_REFRESH_DEBOUNCE_SECONDS
from custom_components.dess_monitor.coordinators.coordinator import MainCoordinator
from custom_components.dess_monitor.sdk import DessmonitorClient, DeviceIdentity, DeviceStream

_LOGGER = logging.getLogger(__name__)


class DeviceStreamManager:
    """Owns one :class:`DeviceStream` per active device on the config entry."""

    def __init__(
            self,
            hass: HomeAssistant,
            client: DessmonitorClient,
            coordinator: MainCoordinator,
    ) -> None:
        self._hass = hass
        self._client = client
        self._coordinator = coordinator
        self._streams: dict[str, DeviceStream] = {}
        self._tasks: dict[str, asyncio.Task[None]] = {}
        self._pending: dict[str, dict[str, Any]] = {}
        self._dirty_pns: set[str] = set()
        self._refresh_handle: asyncio.TimerHandle | None = None
        self._stopped = False
        self._first_frame_logged: set[str] = set()

    async def async_start(self) -> None:
        """Open one stream per device. Idempotent."""
        if self._streams:
            return
        for device in self._coordinator.devices:
            pn = str(device.get("pn"))
            if not pn:
                continue
            try:
                identity = DeviceIdentity.from_dict(device)
            except (KeyError, TypeError, ValueError):
                _LOGGER.warning("Cannot derive identity for %s — skipping WS stream", pn)
                continue
            stream = self._client.stream_device(identity)
            await stream.start()
            self._streams[pn] = stream
            self._tasks[pn] = self._hass.loop.create_task(
                self._consume(pn, stream),
                name=f"dess_monitor.stream({pn})",
            )
        if self._streams:
            _LOGGER.info("WebSocket streams started for %d device(s)", len(self._streams))

    async def async_stop(self) -> None:
        """Tear down every stream and the debounce timer."""
        self._stopped = True
        if self._refresh_handle is not None:
            self._refresh_handle.cancel()
            self._refresh_handle = None
        for task in self._tasks.values():
            task.cancel()
        if self._tasks:
            await asyncio.gather(*self._tasks.values(), return_exceptions=True)
        for stream in self._streams.values():
            try:
                await stream.stop()
            except Exception:
                _LOGGER.exception("Failed to stop WS stream for %s", stream.identity.pn)
        self._streams.clear()
        self._tasks.clear()
        self._dirty_pns.clear()
        self._pending.clear()

    async def _consume(self, pn: str, stream: DeviceStream) -> None:
        try:
            async for frame in stream:
                if self._stopped:
                    break
                self._merge_frame(pn, frame.data)
        except asyncio.CancelledError:
            raise
        except Exception:
            _LOGGER.exception("WS consumer crashed for %s", pn)

    def _merge_frame(self, pn: str, data: dict[str, Any]) -> None:
        coord_data = self._coordinator.data
        if not isinstance(coord_data, dict):
            return
        device_entry = coord_data.get(pn)
        if not isinstance(device_entry, dict):
            return
        if pn not in self._first_frame_logged:
            self._first_frame_logged.add(pn)
            _LOGGER.info(
                "WS first frame for %s: top-level keys=%s",
                pn, sorted(data.keys()) if isinstance(data, dict) else type(data).__name__,
            )
        # Stash the merged payload in the pending buffer keyed by pn — we
        # rebuild the full coordinator dict from coord_data + pending only
        # when the debounce timer fires. Crucially we do NOT mutate
        # ``coordinator.data`` here: ``async_set_updated_data`` short-circuits
        # when the new reference equals the current one (under
        # ``always_update=False``), so an early in-place update silently
        # cancels the listener notification.
        existing_pending = self._pending.get(pn)
        existing_ws = device_entry.get("ws_data") if existing_pending is None else existing_pending.get("ws_data")
        merged_ws = {**existing_ws, **data} if isinstance(existing_ws, dict) else dict(data)
        self._pending[pn] = {
            "ws_data": merged_ws,
            "ws_received_at": time.time(),
        }
        self._dirty_pns.add(pn)
        self._schedule_refresh()

    def _schedule_refresh(self) -> None:
        if self._refresh_handle is not None or self._stopped:
            return
        self._refresh_handle = self._hass.loop.call_later(
            WEBSOCKET_REFRESH_DEBOUNCE_SECONDS,
            self._dispatch_refresh,
        )

    @callback
    def _dispatch_refresh(self) -> None:
        self._refresh_handle = None
        if self._stopped or not self._dirty_pns:
            return
        dirty = self._dirty_pns
        self._dirty_pns = set()
        coord_data = self._coordinator.data
        if not isinstance(coord_data, dict):
            self._pending.clear()
            return
        # Build a NEW top-level dict so listener equality checks see a
        # different reference and rerender entities. Merging in-place would
        # be silently no-op'd by anything diffing on identity.
        new_coord_data = dict(coord_data)
        for pn in dirty:
            patch = self._pending.pop(pn, None)
            if patch is None:
                continue
            existing = new_coord_data.get(pn)
            if not isinstance(existing, dict):
                continue
            new_coord_data[pn] = {**existing, **patch}
        _LOGGER.debug("WS pushing refresh for %d device(s): %s", len(dirty), sorted(dirty))
        # Push directly to listeners WITHOUT going through
        # ``async_set_updated_data``: that helper cancels and reschedules the
        # coordinator's polling timer, so a steady stream of WS frames
        # (faster than ``update_interval``) starves the polled endpoints of
        # ever firing again. Polled subtrees would then sit frozen, and any
        # canonical metric not present in WS (voltages, currents, capacity,
        # temperatures, frequency, ...) would visibly stop updating while
        # power keeps moving — which is exactly the regression we hit.
        self._coordinator.data = new_coord_data
        self._coordinator.last_update_success = True
        self._coordinator.async_update_listeners()
