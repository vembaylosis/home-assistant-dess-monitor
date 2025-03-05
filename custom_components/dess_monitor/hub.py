from __future__ import annotations

from homeassistant.core import HomeAssistant

from .coordinator import MyCoordinator


class Hub:
    manufacturer = "DESS Monitor"

    def __init__(self, hass: HomeAssistant, username: str, coordinator: MyCoordinator = None) -> None:
        self.auth = None
        self._username = username
        self._hass = hass
        self._name = username
        self.coordinator = coordinator
        self._id = username.lower()
        print('init hub', username)
        self.items = []
        self.online = True

    @property
    def hub_id(self) -> str:
        return self._id

    async def init(self):
        devices = self.coordinator.devices
        for device in devices:
            # print(device)
            self.items.append(InverterDevice(f"{device['pn']}", f"{device['devalias']}", device, self))


class InverterDevice:

    def __init__(self, inverter_pn: str, name: str, device_data, hub: Hub) -> None:
        self._id = inverter_pn
        self.hub = hub
        self.device_data = device_data
        self.name = name
        self.firmware_version = f"0.0.1"
        self.model = "DESS Device"

    @property
    def inverter_id(self) -> str:
        return self._id

    @property
    def online(self) -> float:
        return True
