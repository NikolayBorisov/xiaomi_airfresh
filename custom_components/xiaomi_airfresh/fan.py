"""Add support Xiaomi Mi Air Purifier A1 (MJXFJ-150-A1)"""
import asyncio
from enum import Enum
from functools import partial
import logging

from miio import (  # pylint: disable=import-error
    AirFresh,
    Device,  # del
    DeviceException,
)

from typing import Any, Dict, Optional
from collections import defaultdict

import voluptuous as vol  # pylint: disable=import-error

from homeassistant.components.fan import (  # pylint: disable=import-error
    FanEntity,
    PLATFORM_SCHEMA,
    SUPPORT_SET_SPEED,
    DOMAIN,  # added
)
from homeassistant.const import (  # pylint: disable=import-error
    ATTR_ENTITY_ID,
    CONF_HOST,
    CONF_NAME,
    CONF_TOKEN,
)
from homeassistant.exceptions import PlatformNotReady  # pylint: disable=import-error
import homeassistant.helpers.config_validation as cv  # pylint: disable=import-error


_LOGGER = logging.getLogger(__name__)

DEFAULT_NAME = 'Xiaomi Air Fresh'
DATA_KEY = 'fan.xiaomi_airfresh'

CONF_MODEL = 'model'

ATTR_SPEED = 'speed'

ATTR_PM25 = 'pm25'
ATTR_MODE = 'mode'
ATTR_CO2 = 'co2'
ATTR_TEMPERATURE_OUTSIDE = 'temperature_outside'
ATTR_FAVOURITE_SPEED = 'favourite_speed'
ATTR_FILTER_RATE = 'filter_rate'
ATTR_FILTER_DAY = 'filter_day'
ATTR_CONTROL_SPEED = 'control_speed'
ATTR_PTC_ON = 'ptc_on'
ATTR_PTC_STATUS = 'ptc_status'
ATTR_CHILD_LOCK = 'child_lock'
ATTR_SOUND = 'sound'
ATTR_DISPLAY = 'display'

SUCCESS = ['ok']

AVAILABLE_ATTRIBUTES_AIRFRESH = {
    ATTR_PM25: 'pm25',
    ATTR_CO2: 'co2',
    ATTR_MODE: 'mode',
    ATTR_TEMPERATURE_OUTSIDE: 'temperature_outside',
    ATTR_FAVOURITE_SPEED: 'favourite_speed',
    ATTR_FILTER_RATE: 'filter_rate',
    ATTR_FILTER_DAY: 'filter_day',
    ATTR_CONTROL_SPEED: 'control_speed',
    ATTR_PTC_ON: 'ptc_on',
    ATTR_PTC_STATUS: 'ptc_status',
    ATTR_CHILD_LOCK: 'child_lock',
    ATTR_SOUND: 'sound',
    ATTR_DISPLAY: 'display',
}

MODEL_AIRFRESH_A1 = 'dmaker.airfresh.a1'

PLATFORM_SCHEMA = PLATFORM_SCHEMA.extend({
    vol.Required(CONF_HOST): cv.string,
    vol.Required(CONF_TOKEN): vol.All(cv.string, vol.Length(min=32, max=32)),
    vol.Optional(CONF_NAME, default=DEFAULT_NAME): cv.string,
    vol.Optional(CONF_MODEL): vol.In([MODEL_AIRFRESH_A1]),
})

OPERATION_MODES_AIRFRESH = ['Off', 'Auto', 'Sleep', 'Favourite']

ATTR_MODEL = 'model'


class OperationMode(Enum):
    # Supported modes of the Xiaomi Mi Air Purifier A1 (MJXFJ-150-A1)
    Off = 'off'
    Auto = 'auto'
    Sleep = 'sleep'
    Favourite = 'favourite'


AIRFRESH_SERVICE_SCHEMA = vol.Schema(
    {vol.Optional(ATTR_ENTITY_ID): cv.entity_ids})


SERVICE_SET_PTC_ON = "airfresh_set_ptc_on"
SERVICE_SET_PTC_OFF = "airfresh_set_ptc_off"
SERVICE_SET_SOUND_ON = "airfresh_set_sound_on"
SERVICE_SET_SOUND_OFF = "airfresh_set_sound_off"
SERVICE_SET_DISPLAY_ON = "airfresh_set_display_on"
SERVICE_SET_DISPLAY_OFF = "airfresh_set_display_off"
SERVICE_SET_FILTER_RESET = "airfresh_set_filter_reset"
SERVICE_SET_FAVOURITE_SPEED = "airfresh_set_favourite_speed"

SERVICE_SCHEMA_FAVOURITE_SPEED = AIRFRESH_SERVICE_SCHEMA.extend(
    {vol.Required(ATTR_SPEED): vol.All(
        vol.Coerce(int), vol.Clamp(min=0, max=200))}
)

SERVICE_TO_METHOD = {
    SERVICE_SET_PTC_ON: {"method": "async_set_ptc_on"},
    SERVICE_SET_PTC_OFF: {"method": "async_set_ptc_off"},
    SERVICE_SET_FAVOURITE_SPEED: {
        "method": "async_set_favourite_speed",
        "schema": SERVICE_SCHEMA_FAVOURITE_SPEED,
    },
    SERVICE_SET_SOUND_ON: {"method": "async_set_sound_on"},
    SERVICE_SET_SOUND_OFF: {"method": "async_set_sound_off"},
    SERVICE_SET_DISPLAY_ON: {"method": "async_set_display_on"},
    SERVICE_SET_DISPLAY_OFF: {"method": "async_set_display_off"},
    SERVICE_SET_FILTER_RESET: {"method": "async_set_filter_reset"},
}


async def async_setup_platform(hass, config, async_add_entities, discovery_info=None):
    """Set up the miio fan device from config."""
    if DATA_KEY not in hass.data:
        hass.data[DATA_KEY] = {}

    host = config.get(CONF_HOST)
    token = config.get(CONF_TOKEN)
    name = config.get(CONF_NAME)
    model = config.get(CONF_MODEL)

    _LOGGER.info("Initializing with host %s (token %s...)", host, token[:5])
    unique_id = None

    if model is None:
        model = 'dmaker.airfresh.a1'

    if model.startswith('dmaker.airfresh.a1'):
        air_fresh = AirFresh(host, token)
        device = XiaomiAirFreshDevice(name, air_fresh, model, unique_id)
    else:
        _LOGGER.error(
            'This custom components only support Xiaomi Mi Air Purifier A1 (MJXFJ-150-A1)'
            'and provide the following data: %s', model)
        return False

    hass.data[DATA_KEY][host] = device
    async_add_entities([device], update_before_add=True)

    async def async_service_handler(service):
        """Map services to methods on XiaomiAirPurifier."""
        method = SERVICE_TO_METHOD.get(service.service)
        params = {
            key: value for key, value in service.data.items() if key != ATTR_ENTITY_ID
        }
        entity_ids = service.data.get(ATTR_ENTITY_ID)
        if entity_ids:
            devices = [
                device
                for device in hass.data[DATA_KEY].values()
                if device.entity_id in entity_ids
            ]
        else:
            devices = hass.data[DATA_KEY].values()

        update_tasks = []
        for device in devices:
            if not hasattr(device, method["method"]):
                continue
            await getattr(device, method["method"])(**params)
            update_tasks.append(device.async_update_ha_state(True))

        if update_tasks:
            await asyncio.wait(update_tasks)

    for air_purifier_service in SERVICE_TO_METHOD:
        schema = SERVICE_TO_METHOD[air_purifier_service].get(
            "schema", AIRFRESH_SERVICE_SCHEMA
        )
        hass.services.async_register(
            DOMAIN, air_purifier_service, async_service_handler, schema=schema
        )


class AirFreshDeviceStatus:
    """Container for status reports from the air fresh."""

    def __init__(self, data: Dict[str, Any]) -> None:
        self.data = data

    @property
    def power(self) -> bool:
        """Power state."""
        return self.data["power"]

    @property
    def is_on(self) -> bool:
        """Return True if device is on."""
        return self.power == True

    @property
    def pm25(self) -> int:
        """Air quality index."""
        return self.data["pm25"]

    @property
    def co2(self) -> int:
        """Carbon dioxide."""
        return self.data["co2"]

    @property
    def temperature_outside(self) -> int:
        """Temperature Outside."""
        return self.data["temperature_outside"]

    @property
    def favourite_speed(self) -> int:
        """Favourite Speed."""
        return self.data["favourite_speed"]

    @property
    def filter_rate(self) -> int:
        """Filter Rate."""
        return self.data["filter_rate"]

    @property
    def filter_day(self) -> int:
        """Filter Day."""
        return self.data["filter_day"]

    @property
    def control_speed(self) -> int:
        """Control Speed."""
        return self.data["control_speed"]

    @property
    def ptc_on(self) -> bool:
        """Ptc On."""
        return self.data["ptc_on"]

    @property
    def ptc_status(self) -> bool:
        """Ptc Status."""
        return self.data["ptc_status"]

    @property
    def child_lock(self) -> bool:
        """Child Lock."""
        return self.data["child_lock"]

    @property
    def sound(self) -> bool:
        """Sound."""
        return self.data["sound"]

    @property
    def display(self) -> bool:
        """Display."""
        return self.data["display"]

    @property
    def mode(self) -> OperationMode:
        """Current operation mode."""
        return OperationMode(self.data["mode"])

    def __repr__(self) -> str:
        s = "<AirFreshStatus power=%s, " \
            "pm25=%s, " \
            "co2=%s, " \
            "temperature_outside=%s, " \
            "favourite_speed=%s, " \
            "filter_rate=%s, " \
            "filter_day=%s, " \
            "control_speed=%s, " \
            "ptc_on=%s, " \
            "ptc_status=%s, " \
            "child_lock=%s, " \
            "sound=%s, " \
            "display=%s, " \
            "mode=%s>" % \
            (self.power,
             self.pm25,
             self.co2,
             self.temperature_outside,
             self.favourite_speed,
             self.filter_rate,
             self.filter_day,
             self.control_speed,
             self.ptc_on,
             self.ptc_status,
             self.child_lock,
             self.sound,
             self.display,
             self.mode)
        return s

    def __json__(self):
        return self.data


class XiaomiAirFreshDevice(FanEntity):
    """Representation of a generic Xiaomi device."""

    def __init__(self, name, device, model, unique_id):
        """Initialize the generic Xiaomi device."""
        self._name = name
        self._device = device
        self._model = model
        self._unique_id = unique_id

        self._available = False
        self._state = None
        self._state_attrs = {ATTR_MODEL: self._model}
        self._skip_update = False

        self._available_attributes = AVAILABLE_ATTRIBUTES_AIRFRESH
        self._speed_list = OPERATION_MODES_AIRFRESH
        self._state_attrs.update(
            {attribute: None for attribute in self._available_attributes})

    @property
    def supported_features(self):
        """Flag supported features."""
        return SUPPORT_SET_SPEED

    @property
    def should_poll(self):
        """Poll the device."""
        return True

    @property
    def unique_id(self):
        """Return an unique ID."""
        return self._unique_id

    @property
    def name(self):
        """Return the name of the device if any."""
        return self._name

    @property
    def available(self):
        """Return true when state is known."""
        return self._available

    @property
    def device_state_attributes(self):
        """Return the state attributes of the device."""
        return self._state_attrs

    @property
    def is_on(self):
        """Return true if device is on."""
        return self._state

    @property
    def speed_list(self) -> list:
        """Get the list of available speeds."""
        return self._speed_list

    @property
    def speed(self):
        """Return the current speed."""
        if self._state:
            return OperationMode(self._state_attrs[ATTR_MODE]).name

        return None

    @staticmethod
    def _extract_value_from_attribute(state, attribute):
        value = getattr(state, attribute)
        if isinstance(value, Enum):
            return value.value

        return value

    def get_status(self):
        properties = [
            "power",
            "pm25",
            "co2",
            "temperature_outside",
            "favourite_speed",
            "filter_rate",
            "filter_day",
            "control_speed",
            "ptc_on",
            "ptc_status",
            "child_lock",
            "sound",
            "display",
            "mode"
        ]

        # A single request is limited to 16 properties. Therefore the
        # properties are divided into multiple requests
        _props = properties.copy()
        values = []
        while _props:
            values.extend(self._device.send("get_prop", _props[:4]))
            _props[:] = _props[4:]

        properties_count = len(properties)
        values_count = len(values)
        if properties_count != values_count:
            _LOGGER.debug(
                "Count (%s) of requested properties does not match the "
                "count (%s) of received values.",
                properties_count, values_count)
        return AirFreshDeviceStatus(
            defaultdict(lambda: None, zip(properties, values)))

    async def async_update(self):
        """Fetch state from the device."""

        # On state change the device doesn't provide the new state immediately.
        if self._skip_update:
            self._skip_update = False
            return

        try:
            state = await self.hass.async_add_executor_job(
                self.get_status)
            _LOGGER.debug("Got new state: %s", state)

            self._available = True
            self._state = state.is_on
            self._state_attrs.update(
                {key: self._extract_value_from_attribute(state, value) for
                 key, value in self._available_attributes.items()})

        except DeviceException as ex:
            self._available = False
            _LOGGER.error("Got exception while fetching the state: %s", ex)

    async def _try_command(self, mask_error, *args, **kwargs):
        """Call a miio device command handling error messages."""
        try:
            result = await self.hass.async_add_executor_job(
                partial(self._device.send, *args, **kwargs))

            _LOGGER.debug("Response received from miio device: %s", result)

            return result == SUCCESS
        except DeviceException as exc:
            _LOGGER.error(mask_error, exc)
            self._available = False
            return False

    async def send_raw_cmd(self, mask_error, command, parameters):
        """Send a raw command to the device."""
        _LOGGER.debug("sending cmd %s %s", command, parameters)
        result = await self._try_command(mask_error, command, parameters)
        return result

    async def async_turn_on(self, speed: str = None, **kwargs) -> None:
        """Turn the device on."""
        if speed:
            # If operation mode was set the device must not be turned on.
            await self.async_set_speed(speed)
        else:
            await self.send_raw_cmd("Turning the miio device on failed.", "set_power", [True])

    async def async_turn_off(self, **kwargs) -> None:
        """Turn the device off."""
        await self.send_raw_cmd("Turning the miio device off failed.", "set_power", [False])

    async def async_set_speed(self, speed: str) -> None:
        """Set the speed of the fan."""
        if SUPPORT_SET_SPEED == 0:
            return

        _LOGGER.debug("Setting the operation mode to: %s", speed)
        if OperationMode[speed.title()].value == 'off':
            await self.async_turn_off()
        else:
            await self.send_raw_cmd(
                "Setting operation mode of the miio device failed.",
                "set_mode", OperationMode[speed.title()].value)

    async def async_set_ptc_on(self, **kwargs) -> None:
        """Turn the ptc on."""
        _LOGGER.debug("Setting the ptc to on")
        await self.send_raw_cmd("Turning the ptc of the miio device on failed.", "set_ptc_on", [True])

    async def async_set_ptc_off(self, **kwargs) -> None:
        """Turn the ptc off."""
        _LOGGER.debug("Setting the ptc to off")
        await self.send_raw_cmd("Turning the ptc of the miio device off failed.", "set_ptc_on", [False])

    async def async_set_favourite_speed(self, speed: str, **kwargs) -> None:
        """Set the favourite speed of the freshair."""
        _LOGGER.debug("Setting the favourite speed to: %s", speed)
        await self.send_raw_cmd("Setting favourite speed of the miio device failed.", "set_favourite_speed", [speed])

    async def async_set_sound_on(self, **kwargs) -> None:
        """Turn the sound on."""
        _LOGGER.debug("Setting the sound to on")
        await self.send_raw_cmd("Turning the sound of the miio device on failed.", "set_sound_on", [True])

    async def async_set_sound_off(self, **kwargs) -> None:
        """Turn the sound off."""
        _LOGGER.debug("Setting the sound to off")
        await self.send_raw_cmd("Turning the sound of the miio device off failed.", "set_sound_on", [False])

    async def async_set_display_on(self, **kwargs) -> None:
        """Turn the display on."""
        _LOGGER.debug("Setting the display to on")
        await self.send_raw_cmd("Turning the display of the miio device on failed.", "set_display_on", [True])

    async def async_set_display_off(self, **kwargs) -> None:
        """Turn the display off."""
        _LOGGER.debug("Setting the display to off")
        await self.send_raw_cmd("Turning the display of the miio device off failed.", "set_display_on", [False])

    async def async_set_filter_reset(self, **kwargs) -> None:
        """Reset airfresh filter."""
        _LOGGER.debug("Setting the filter reset")
        await self.send_raw_cmd("Reset filter on miio device failed.", "set_filter_reset", [True])
