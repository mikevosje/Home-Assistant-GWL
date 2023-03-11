from homeassistant.core import HomeAssistant
from homeassistant.components.sensor import (
    RestoreSensor,
    SensorDeviceClass,
    STATE_CLASS_MEASUREMENT
)
from datetime import timedelta, datetime
import logging
from .BaseClass import BaseClass
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
import sqlite3
from sqlite3 import Error
_LOGGER = logging.getLogger(__name__)

class GasWaterLichtSensor(BaseClass, RestoreSensor):
    def __init__(
        self, 
        hass: HomeAssistant,
        type,
        sensor_friendly_name,
        positive_entities,
        negative_entities = []
    ):
        super(GasWaterLichtSensor, self).__init__(hass, type)
        # Common.
        self.entity_id = f"sensor.{DOMAIN}_{type}"
        self._sensor_friendly_name = sensor_friendly_name
        self.friendly_name = f"{type.capitalize()} usage this month"
        
        # Sensor specific.
        self.this_month_costs = 0
        self._pos_sources = positive_entities
        self._neg_sources = negative_entities

        _LOGGER.debug(f"[{self.entity_id}] Positive entities: {positive_entities}")
        _LOGGER.debug(f"[{self.entity_id}] Negative entities: {negative_entities}")

        self._current_month = datetime.now().month

        if self._type == 'gas':
            self.this_month_cap = PRICE_CAP_GAS_MONTH[self._current_month]
            self._price = GAS_PRICE

            # Entity specific.
            self._attr_device_class = SensorDeviceClass.GAS
            self._attr_unit_of_measurement = UNIT_OF_MEASUREMENT_GAS
        else:
            self.this_month_cap = PRICE_CAP_POWER_MONTH[self._current_month]
            self._price = POWER_PRICE

            # Entity specific.
            self._attr_device_class = SensorDeviceClass.ENERGY
            self._attr_unit_of_measurement = UNIT_OF_MEASUREMENT_POWER

        try:
            self._dbconnection = sqlite3.connect('../config/home-assistant_v2.db')
        except Error as e:
            _LOGGER.error(e)
            raise Exception(e)

        self._state = None;

    @property
    def extra_state_attributes(self):
        return {
            ATTR_FRIENDLY_NAME: self.friendly_name,
            ATTR_THIS_MONTH_CAP: self.this_month_cap,
            ATTR_THIS_MONTH_COSTS: round(self.this_month_costs, PRECISION),
            ATTR_UNIT_OF_MEASUREMENT: self._attr_unit_of_measurement
        }

    async def _getData(self):
        # Checking if we have entered a new month.
        now_month = datetime.now().month
        if self._current_month is not now_month:
            # If so.. change the cap to new values.
            self._current_month = now_month
            if self._type == 'gas':
                self.this_month_cap = PRICE_CAP_GAS_MONTH[self._current_month]
            else:
                self.this_month_cap = PRICE_CAP_POWER_MONTH[self._current_month]

        # Positive entities are consumers.
        pos_usage = 0        
        for entity_id in self._pos_sources:
            stat_id = await self._getStatisticsId(entity_id);
            pos_usage += await self._get_value(stat_id)
        # _LOGGER.debug(f"[{self.entity_id}] In update pos_usage is {pos_usage}")

        # Negative entities are producers like solar panels.
        neg_usage = 0
        for entity_id in self._neg_sources:
            stat_id = await self._getStatisticsId(entity_id);
            neg_usage += await self._get_value(stat_id)
        # _LOGGER.debug(f"[{self.entity_id}] In update neg_usage is {neg_usage}")

        total_usage = pos_usage - neg_usage
        # _LOGGER.debug(f"[{self.entity_id}] In update total_usage is {total_usage}")
        # if total_usage < 0:
        #     total_usage = 0           

        self._state = total_usage
        self.this_month_costs = self._state * self._price
        # To make sure we don't get negative costs..
        if self.this_month_costs < 0: self.this_month_costs = 0

    async def _get_value(self, statistics_metadata_id):
        state_old = await self._get_first_recorded_state_in_month(statistics_metadata_id)
        _LOGGER.debug(state_old)
        if state_old is None:
            # _LOGGER.error('Unable to find historic value for entity "%s". Skipping..', entity_id)
            return 0
        try:
            usage = float(state_old)
            # _LOGGER.debug(f"Getting first recorded state of this month for: {entity_id} resulted in: {usage}")
        except ValueError:
            # _LOGGER.warning(f"Unable to convert the first recorded state of this month for: {entity_id} to float..Value is: {state_old.state}. Setting usage to 0.")
            usage = 0

        return usage 

    async def _get_first_recorded_state_in_month(self, statistics_metadata_id: str):    
        start_date = await self._convert_time_to_utc(datetime.now().today().replace(day=1, hour=0, minute=0, second=0, microsecond=0))
        end_date = datetime.now()

        # _LOGGER.debug(
        #         f"start_date for entity {statistics_metadata_id} is {start_date}"
        #     )
        # _LOGGER.debug(
        #         f"end_date for entity {statistics_metadata_id} is {end_date}"
        #     )

        try:
            cursor = self._dbconnection.cursor()
            # _LOGGER.debug(f"SELECT MAX(state) - MIN(state) AS total_import FROM statistics WHERE metadata_id = '{statistics_metadata_id}' AND created >= datetime('{start_date}') AND created <= datetime('{end_date}');")
            cursor.execute(f"SELECT MAX(state) - MIN(state) AS total_import FROM statistics WHERE metadata_id = '{statistics_metadata_id}' AND created_ts >= unixepoch('{start_date}') AND created_ts <= unixepoch('{end_date}');")
            record = cursor.fetchone()
            # _LOGGER.debug(record)
            if(record == None):
                return 0
            else:
                return record[0]
        except Error as e:
            _LOGGER.error(e)
            raise Exception(e)

    # async def _get_first_recorded_state_in_month(self, entity_id: str):    
    #     start_time = await self._convert_time_to_utc(datetime.now().today().replace(day=1, hour=0, minute=0, second=0, microsecond=0))
    #     end_time = await self._convert_time_to_utc(datetime.now())

    #     history_list = await get_instance(self.hass).async_add_executor_job(
    #         history.state_changes_during_period,
    #         self.hass,
    #         start_time,
    #         end_time,
    #         str(entity_id),
    #         False,
    #         False,
    #         1
    #     )
    #     if (
    #         entity_id not in history_list.keys()
    #         or history_list[entity_id] is None
    #         or len(history_list[entity_id]) == 0
    #     ):
    #         # _LOGGER.warning(
    #         #     'Historical data not found for entity "%s". Total usage may be off.', entity_id
    #         # )
    #         return None
    #     else:
    #         return history_list[entity_id][0]