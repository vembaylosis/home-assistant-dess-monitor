from __future__ import annotations

from typing import Any, cast

from ..models import CtrlFieldsResponse, CtrlValueResponse, DeviceIdentity, DirectCommandResponse
from ..session import Session


class ControlResource:
    """Read and write device control parameters, plus low-level direct commands.

    All endpoints currently route through ``/public/``; the ``/remote/`` endpoint
    is reachable via :meth:`Session.request` with ``endpoint='remote'`` if a future
    use case requires it.
    """

    def __init__(self, session: Session) -> None:
        self._session = session

    async def get_value(
        self,
        identity: DeviceIdentity,
        param_id: str,
    ) -> CtrlValueResponse:
        """Read a single control parameter value.

        Some parameters legitimately return non-zero ``err`` for unsupported devices,
        so this method uses ``raise_on_error=False`` and returns the raw envelope on
        failure. Detect failure via ``'err' in result``; on success the response is
        the ``dat`` payload (``{'val': ...}``) without an ``err`` key.
        """
        return cast(
            CtrlValueResponse,
            await self._session.request(
                "queryDeviceCtrlValue",
                {
                    "i18n": "en_US",
                    "source": "1",
                    "id": param_id,
                    **identity.as_params(),
                },
                raise_on_error=False,
            ),
        )

    async def get_fields(self, identity: DeviceIdentity) -> CtrlFieldsResponse:
        return cast(
            CtrlFieldsResponse,
            await self._session.request(
                "queryDeviceCtrlField",
                {"i18n": "en_US", "source": "1", **identity.as_params()},
            ),
        )

    async def set_param(
        self,
        identity: DeviceIdentity,
        param_id: str,
        value: str,
    ) -> dict[str, Any]:
        """Write a control parameter. The API returns a permissive ack envelope
        whose contents the SDK doesn't enumerate."""
        return cast(
            dict[str, Any],
            await self._session.request(
                "ctrlDevice",
                {
                    "i18n": "en_US",
                    "source": "1",
                    "id": param_id,
                    "val": value,
                    **identity.as_params(),
                },
            ),
        )

    async def send_direct_command(
        self,
        identity: DeviceIdentity,
        cmd_hex: str,
    ) -> DirectCommandResponse:
        """Send a raw inverter command (already encoded to hex).

        Use the ``commands`` module / helpers for converting a logical command name
        (e.g. ``QPIGS``) into the hex payload this method expects. The response
        ``dat`` is the inverter's reply, also hex-encoded — decode with the
        matching command codec.
        """
        return cast(
            DirectCommandResponse,
            await self._session.request(
                "sendCmdToDevice",
                {"source": "1", "cmd": cmd_hex, **identity.as_params()},
            ),
        )
