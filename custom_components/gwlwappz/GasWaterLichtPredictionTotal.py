from homeassistant.core import HomeAssistant
from homeassistant.components.sensor import (
    RestoreSensor,
    SensorDeviceClass,
    STATE_CLASS_MEASUREMENT
)
from datetime import timedelta, datetime
from calendar import monthrange
from dateutil.relativedelta import relativedelta
from calendar import monthrange
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
_LOGGER = logging.getLogger(__name__)

class GasWaterLichtPredictionTotalSensor(BaseClass, RestoreSensor):
    def __init__(
        self, 
        hass: HomeAssistant,
        type,
        name,
        sensor_friendly_name,
        end_date_contract,
        till_end_date_contract,
        positive_entities,
        negative_entities = [],
    ):
        super(GasWaterLichtPredictionTotalSensor, self).__init__(hass, type)
        self.entity_id = sensor_friendly_name
        self.friendly_name = name
        
        # Sensor specific.
        self.this_month_costs = 0
        self._pos_sources = positive_entities
        self._neg_sources = negative_entities
        self._sensor_friendly_name = sensor_friendly_name
        self._end_date_contract = end_date_contract
        self._till_end_date_contract = till_end_date_contract
        self._type = type

        # _LOGGER.debug(f"[{self.entity_id}] Positive entities: {positive_entities}")
        # _LOGGER.debug(f"[{self.entity_id}] Negative entities: {negative_entities}")
        # _LOGGER.debug(f"[{self.entity_id}] End date contract: {end_date_contract}")

        # Setting state to none as we are waiting for the update.
        self._state = None;


    @property
    def extra_state_attributes(self):
        return {
            ATTR_FRIENDLY_NAME: self.friendly_name,
            ATTR_UNIT_OF_MEASUREMENT: self._attr_unit_of_measurement
        }

    async def _getData(self):
        pos_usage = 0        
        for entity_id in self._pos_sources:
            stat_id = await self._getStatisticsId(entity_id);
            pos_usage += await self._get_value(stat_id)

        _LOGGER.debug(f"[{self.entity_id}] pos usage {pos_usage}")
        pos_end_value = await self._calculate_end_value(pos_usage)


        _LOGGER.debug(f"[{self.entity_id}] pos end usage {pos_end_value}")

        # total_usage = pos_end_value
        # _LOGGER.debug(f"[{self.entity_id}] In update total_usage is {total_usage}")
        # if total_usage < 0:
        #     total_usage = 0           

        neg_usage = 0
        for entity_id in self._neg_sources:
            stat_id = await self._getStatisticsId(entity_id);
            neg_usage += await self._get_value(stat_id)

        _LOGGER.debug(f"[{self.entity_id}] neg usage {neg_usage}")

        total_usage = pos_end_value - neg_usage

        _LOGGER.debug(f"[{self.entity_id}] total usage {total_usage}")

        self._state = total_usage
        
        if(self._type == 'gas'):
            # Entity specific.
            self._attr_device_class = SensorDeviceClass.GAS
            self._attr_unit_of_measurement = UNIT_OF_MEASUREMENT_GAS
        else:
            # Entity specific.
            self._attr_device_class = SensorDeviceClass.ENERGY
            self._attr_unit_of_measurement = UNIT_OF_MEASUREMENT_POWER
        # self.this_month_costs = self._state * self._price
        # To make sure we don't get negative costs..
        # if self.this_month_costs < 0: self.this_month_costs = 0

    async def _calculate_end_value(self, value):
        currentDay = datetime.now().today().day
        daysInMonth = monthrange(datetime.now().year, datetime.now().month)[1]

        _LOGGER.debug(f"[{self.entity_id}] currentDay {currentDay}")
        _LOGGER.debug(f"[{self.entity_id}] daysInMonth {daysInMonth}")

        calculation = (float(value) / currentDay) * daysInMonth
        _LOGGER.debug(f"[{self.entity_id}] calculation {calculation}")

        # _LOGGER.debug(f"[{self.entity_id}] old state is {state_old}")
        if value is None:
            # _LOGGER.error('Unable to find historic value for entity "%s". Skipping..', statistics_metadata_id)
            return 0
        try:
            usage = float(calculation)
            # _LOGGER.debug(f"Getting first recorded state of this month for: {statistics_metadata_id} resulted in: {usage}")
        except ValueError:
            # _LOGGER.warning(f"Unable to convert the first recorded state of this month for: {statistics_metadata_id} to float..Value is: {state_old.state}. Setting usage to 0.")
            usage = 0

        return usage 

    async def _get_value(self, statistics_metadata_id):
        state_old = await self._get_first_recorded_state_in_month(statistics_metadata_id)

        # _LOGGER.debug(f"[{self.entity_id}] old state is {state_old}")
        if state_old is None:
            # _LOGGER.error('Unable to find historic value for entity "%s". Skipping..', statistics_metadata_id)
            return 0
        try:
            usage = float(state_old)
            # _LOGGER.debug(f"Getting first recorded state of this month for: {statistics_metadata_id} resulted in: {usage}")
        except ValueError:
            # _LOGGER.warning(f"Unable to convert the first recorded state of this month for: {statistics_metadata_id} to float..Value is: {state_old.state}. Setting usage to 0.")
            usage = 0

        return usage 

    async def _get_first_recorded_state_in_month(self, statistics_metadata_id: str):  
        actualMonth = datetime.now().month  
        actualYear = datetime.now().year
        startOfMonth = datetime.now().today().replace(day=1, month=actualMonth, year=actualYear, hour=0, minute=0, second=0, microsecond=0)
        endOfMonth = startOfMonth + relativedelta(months=1)
        start_date = await self._convert_time_to_utc(startOfMonth)
        end_date = await self._convert_time_to_utc(endOfMonth)

        try:
            cursor = self._dbconnection.cursor()
            # _LOGGER.debug(f"SELECT MAX(state) - MIN(state) AS total_import FROM statistics WHERE metadata_id = '{statistics_metadata_id}' AND created_ts >= unixepoch('{start_date}') AND created_ts <= unixepoch('{end_date}');")
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