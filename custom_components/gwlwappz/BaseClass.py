from homeassistant.core import HomeAssistant
from _sha1 import sha1
from .const.const import (
    ATTR_FRIENDLY_NAME,
    ATTR_THIS_MONTH_CAP,
    ATTR_THIS_MONTH_COSTS,
    ATTR_UNIT_OF_MEASUREMENT,
    CONF_SOURCES_TOTAL_GAS,
    CONF_SOURCES_TOTAL_POWER,
    CONF_SOURCES_TOTAL_SOLAR,
    DOMAIN,
    GAS_PRICE,
    ICON,
    POWER_PRICE,
    PRECISION,
    PRICE_CAP_GAS_MONTH,
    PRICE_CAP_POWER_MONTH,
    UNIT_OF_MEASUREMENT_GAS,
    UNIT_OF_MEASUREMENT_POWER,
    UPDATE_MIN_TIME
)
import logging
from homeassistant.components.sensor import (
    RestoreSensor,
    SensorDeviceClass,
    STATE_CLASS_MEASUREMENT
)
import sqlite3
from sqlite3 import Error
import pytz
from datetime import timedelta, datetime

_LOGGER = logging.getLogger(__name__)

class BaseClass(object):
    def __init__(
        self, 
        hass: HomeAssistant,
        type
    ):
        self._type = type
        try:
            self._dbconnection = sqlite3.connect('../config/home-assistant_v2.db')
        except Error as e:
            _LOGGER.error(e)
            raise Exception(e)

    @property
    def unique_id(self):
        return str(
            sha1(
                self._sensor_friendly_name.encode("utf-8")
            ).hexdigest()
        )

    @property
    def name(self):
        return self.friendly_name

    @property
    def icon(self):
        return ICON

    @property
    def state(self):
        if self._state is not None:
            return round(self._state, PRECISION)
        return self._state

    @property
    def state_class(self):
        return STATE_CLASS_MEASUREMENT

    async def async_update(self):
        await self._getData()

    async def _getStatisticsId(self, entity_id):
        try:
            cursor = self._dbconnection.cursor()
            cursor.execute(f"SELECT id FROM statistics_meta WHERE statistic_id = '{entity_id}'")
            return cursor.fetchone()[0]
        except Error as e:
            _LOGGER.error(e)
            raise Exception(e)

    async def _convert_time_to_utc(self, datetime):
        local = pytz.timezone("Europe/Amsterdam")
        local_dt = local.localize(datetime, is_dst=None)
        utc_dt = local_dt.astimezone(pytz.utc)

        return utc_dt