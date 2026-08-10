from __future__ import annotations
from typing import TYPE_CHECKING, Optional, List
import asyncio
import json
import logging

from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers import device_registry as dr, entity_registry as er
from homeassistant.components import persistent_notification
from .const import DOMAIN

if TYPE_CHECKING:
    from .coordinator import BluettiDeviceCoordinator  # pragma: no cover

__LOGGER__ = logging.getLogger(__name__)

manufacturer = "Bluetti"

class BluettiData:
    """Data for the BLUETTI integration."""

    def __init__(self, hass, devices: Optional[List[dict]] = None):
        self.devices = [
            BluettiDevice(
                device_id=dev.sn,
                on_line=dev.online or '0',
                name=dev.name,
                sn=dev.sn,
                model=dev.model,
                state_list=dev.stateList or []
            )
            for dev in devices or []
        ]
        self.loop = hass.loop

    async def test_connection(self) -> bool:
        """Test connectivity to devices."""
        await asyncio.sleep(0.1)
        return True

    def get_device_by_sn(self, sn):
        for dev in self.devices:
            if dev.device_id == sn:
                return dev
        return None

    def web_socket_message_handler(self, message: str):
        __LOGGER__.debug("Received BLUETTI websocket message: %s", message)

        res = json.loads(message)
        sn = res["data"]["deviceSn"]

        device = self.get_device_by_sn(sn)
        if device and device.coordinator:
            # This runs on the websocket thread, not the event loop, so a
            # thread-safe scheduling call is required here.
            asyncio.run_coroutine_threadsafe(
                device.coordinator.async_request_refresh(), self.loop
            )

class BluettiState:
    """Represents a single function/state of the device."""

    def __init__(self, fn_code: str, fn_name: str, fn_value: str, fn_type: str, support_mode_values: Optional[List[dict]] = None, sensor_info:dict=None):
        self.fn_code = fn_code
        self.fn_name = fn_name
        self.fn_value = fn_value
        self.fn_type = fn_type
        self.support_mode_values = support_mode_values or []
        self.sensor_info = sensor_info or {}

    def is_switch(self) -> bool:
        return len(self.support_mode_values) == 0

    def set_value(self, value: str):
        """Set the state value, validate if mode selection."""
        if self.is_switch() or any(v["code"] == value for v in self.support_mode_values):
            self.fn_value = value
        else:
            raise ValueError(f"Invalid value {value} for {self.fn_code}")

    def get_name_for_value(self) -> str:
        """Return human-readable name for current value."""
        if self.is_switch():
            return "On" if self.fn_value == "1" else "Off"
        for v in self.support_mode_values:
            if v["code"] == self.fn_value:
                return v["name"]
        return self.fn_value

    def __repr__(self):
        return f"<BluettiState {self.fn_code}={self.fn_value}>"


class BluettiDevice:
    """Represents a single Bluetti device."""

    def __init__(self, device_id: str, on_line: str, name: str, sn: str, model: str, state_list: Optional[List[dict]] = None):
        self.device_id = device_id
        self.on_line = on_line
        self.name = name
        self.sn = sn
        self.model = model
        self.manufacturer = manufacturer
        self.coordinator: "BluettiDeviceCoordinator | None" = None
        self.states = [
            BluettiState(
                fn_code=s.get("fnCode"),
                # Some fn_codes are not localized by the API and come back
                # with an empty fnName; fall back to fn_code so entities
                # never end up with a blank has_entity_name name (which
                # Home Assistant displays using the raw entity_id instead).
                fn_name=s.get("fnName") or s.get("fnCode") or "",
                fn_value=s.get("fnValue"),
                fn_type=s.get("fnType"),
                support_mode_values=s.get("supportModeValues"),
                sensor_info = s.get("sensorInfo")
            )
            for s in state_list or []
        ]

        self._api_client = None
        self._unbind_processed = False
        self._hass = None
        self._entry = None
        self._entry_id = None

    def __repr__(self):
        return f"<BluettiDevice id={self.device_id} name={self.name}>"

    def get_state(self, fn_code: str) -> Optional[BluettiState]:
        """Return state object by fn_code."""
        for s in self.states:
            if s.fn_code == fn_code:
                return s
        return None

    async def set_state_value(self, fn_code: str, value: str) -> None:
        """Send a control command to the device and notify the coordinator."""
        state = self.get_state(fn_code)
        if not state:
            raise ValueError(f"No state with code {fn_code}")

        try:
            result = await self._api_client.control_device(
                {'sn': self.device_id, 'fnCode': fn_code, 'fnValue': value}
            )
        except Exception as err:
            raise HomeAssistantError(
                translation_domain=DOMAIN,
                translation_key="command_failed",
                translation_placeholders={"device_id": self.device_id, "error": str(err)},
            ) from err

        if result.msgCode == 0:
            state.set_value(value)

        if self.coordinator:
            self.coordinator.async_set_updated_data(self)

    @property
    def online(self) -> bool:
        return self.on_line == '1'

    @property
    def battery_level(self) -> int:
        state = self.get_state("SOC")
        if state:
            return int(state.fn_value)
        return 0

    async def async_refresh_from_api(self) -> None:
        """Fetch the latest state from the BLUETTI cloud API and apply it.

        Raises on any failure so the coordinator can classify and surface it.
        """
        device_status = await self._api_client.get_device_status(self.device_id)
        if not device_status.data:
            raise RuntimeError(f"Empty status response for device {self.device_id}")
        data = device_status.data[0]

        if data.sn != self.device_id:
            return

        if data.isBindByCurUser == '0' and not self._unbind_processed:
            await self._handle_unbind()
            return

        self.on_line = data.online

        for s in data.stateList:
            state_obj = self.get_state(s["fnCode"])
            if state_obj:
                state_obj.fn_value = s["fnValue"]

    async def _handle_unbind(self):
        """Handle device unbinding: Clean up the device, entity, and configuration, and display the notification."""
        self._unbind_processed = True
        
        __LOGGER__.info("Detected device unbinding: %s (%s)", self.name, self.device_id)
        
        # Check if the necessary references exist
        if not self._hass or not self._entry:
            __LOGGER__.error(
                "Cannot handle device unbinding: missing necessary references "
                "(hass=%s, entry=%s)",
                self._hass is not None, self._entry is not None,
            )
            return

        hass = self._hass
        entry = self._entry
        entry_id = self._entry_id or entry.entry_id

        try:
            __LOGGER__.info("Start handling device unbinding: %s", self.device_id)

            # 1. Get the device registry and entity registry
            device_registry = dr.async_get(hass)
            entity_registry = er.async_get(hass)

            # 2. Find and delete all entities of the device
            device_entry = None
            for dev_entry in dr.async_entries_for_config_entry(device_registry, entry_id):
                if (DOMAIN, self.device_id) in dev_entry.identifiers:
                    device_entry = dev_entry
                    break

            if device_entry:
                # Delete all entities of the device
                entities_to_remove = []
                for entity_entry in er.async_entries_for_config_entry(entity_registry, entry_id):
                    if entity_entry.device_id == device_entry.id:
                        entities_to_remove.append(entity_entry.entity_id)

                for entity_id in entities_to_remove:
                    try:
                        entity_registry.async_remove(entity_id)
                        __LOGGER__.debug("Deleted entity: %s", entity_id)
                    except Exception as e:
                        __LOGGER__.warning("Error deleting entity %s: %s", entity_id, e)

                # 3. Delete the device registry
                try:
                    device_registry.async_remove_device(device_entry.id)
                    __LOGGER__.debug("Deleted device registry: %s", device_entry.id)
                except Exception as e:
                    __LOGGER__.warning("Error deleting device registry: %s", e)
            else:
                __LOGGER__.warning("Device registry not found: %s", self.device_id)

            # 4. Remove the device (and its coordinator) from the runtime data
            try:
                runtime_data = getattr(entry, "runtime_data", None)
                if runtime_data:
                    runtime_data.bluetti_devices.devices = [
                        d for d in runtime_data.bluetti_devices.devices
                        if d.device_id != self.device_id
                    ]
                    runtime_data.coordinators.pop(self.device_id, None)
                    __LOGGER__.debug("Removed device from runtime data: %s", self.device_id)
            except Exception as e:
                __LOGGER__.warning("Error removing device from runtime data: %s", e)

            # 5. Remove the device from the configuration entry
            try:
                current_options = dict(entry.options)
                current_devices = current_options.get("devices", [])

                if self.device_id in current_devices:
                    new_devices = [d for d in current_devices if d != self.device_id]

                    hass.config_entries.async_update_entry(
                        entry,
                        options={**current_options, "devices": new_devices}
                    )
                    __LOGGER__.debug("Removed device from configuration entry: %s", self.device_id)
                else:
                    __LOGGER__.warning(
                        "Device %s not in the device list of the configuration entry",
                        self.device_id,
                    )
            except Exception as e:
                __LOGGER__.error("Error updating configuration entry: %s", e, exc_info=True)
                # Even if the update fails, continue to display the notification

            # 6. Display persistent notification
            try:
                notification_id = f"bluetti_unbind_{self.device_id}"
                notification_title = "BLUETTI device has been unbound"
                notification_message = (
                    f"Device **{self.name}** ({self.device_id}) has been unbound in the cloud, "
                    f"and has been automatically removed from the Home Assistant integration.\n\n"
                    f"If this is a mistake, please re-add the device."
                )

                persistent_notification.async_create(
                    hass,
                    title=notification_title,
                    message=notification_message,
                    notification_id=notification_id
                )
                __LOGGER__.debug("Displayed unbinding notification: %s", self.device_id)
            except Exception as e:
                __LOGGER__.warning("Error displaying notification: %s", e)

            # 7. Reload the configuration entry after a delay (ensure all cleanup operations are completed)
            async def _reload_after_cleanup():
                try:
                    await asyncio.sleep(1)  # Delay 1 second to ensure all cleanup operations are completed
                    await hass.config_entries.async_reload(entry_id)
                    __LOGGER__.info("Reloaded configuration entry: %s", entry_id)
                except Exception as e:
                    __LOGGER__.error("Error reloading configuration entry: %s", e, exc_info=True)

            hass.async_create_task(_reload_after_cleanup())

            __LOGGER__.info("Device unbinding processing completed: %s", self.device_id)

        except Exception as e:
            __LOGGER__.error("Error handling device unbinding: %s", e, exc_info=True)
