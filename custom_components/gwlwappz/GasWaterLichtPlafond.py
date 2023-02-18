from homeassistant.core import HomeAssistant
from homeassistant.components.sensor import (
    RestoreSensor,
    SensorDeviceClass,
    STATE_CLASS_MEASUREMENT
)
from datetime import timedelta, datetime
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

class GasWaterLichtPlafondSensor(BaseClass, RestoreSensor):
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
        super(GasWaterLichtPlafondSensor, self).__init__(hass, type)
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

    async def _getPlafond(self):
        self._plafond_max = 0

        if self._type == 'gas':
            type = PRICE_CAP_GAS_MONTH
        else:
            type = PRICE_CAP_POWER_MONTH

        plafond_max = 0
        dt = datetime.strptime(self._end_date_contract, '%Y-%m-%d')
        end_contract_month = dt.month
        end_contract_day = dt.day
        days_in_month = monthrange(datetime.now().year, end_contract_month)[1]

        if(self._till_end_date_contract):
            for x in range(end_contract_month - 1):
                plafond_max += type[x + 1]

            last_month = type[end_contract_month];
            plafond_max += (last_month / days_in_month) * end_contract_day

        else:
            for x in range(12 - end_contract_month):
                plafond_max += type[x + (end_contract_month + 1)]

            first_month = type[end_contract_month]
            plafond_max += (first_month / days_in_month) * (days_in_month - end_contract_day)

        self._plafond_max = plafond_max

    async def _getData(self):
        await self._getPlafond()

        # pos_usage = 0        
        # for entity_id in self._pos_sources:
        #     stat_id = await self._getStatisticsId(entity_id);
        #     pos_usage += await self._get_value(stat_id)
            

        # # Negative entities are producers like solar panels.
        # neg_usage = 0
        # for entity_id in self._neg_sources:
        #     stat_id = await self._getStatisticsId(entity_id);
        #     neg_usage += await self._get_value(stat_id)
        # # _LOGGER.debug(f"[{self.entity_id}] In update neg_usage is {neg_usage}")

        total_usage = self._plafond_max
        # _LOGGER.debug(f"[{self.entity_id}] In update total_usage is {total_usage}")
        # if total_usage < 0:
        #     total_usage = 0           

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

    async def _get_value(self, statistics_metadata_id):
        state_old = await self._get_first_recorded_state_in_month(statistics_metadata_id, self._end_date_contract, self._till_end_date_contract)
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

        

        # Fetching what the entity has for state now.
        # state_now = self.hass.states.get(entity_id)
        # if state_now is None:
        #     _LOGGER.error('Unable to find entity "%s". Skipping..', entity_id)
        #     return None
        # usage_now = float(state_now.state)
        # _LOGGER.debug(f"Getting current state for {entity_id} resulted in: {usage_now}")

        return usage 

    async def _get_first_recorded_state_in_month(self, statistics_metadata_id: str, end_date_contract, till_end_date_contract):    
        dt = datetime.strptime(end_date_contract, '%Y-%m-%d')
        end_contract_month = dt.month
        end_contract_day = dt.day

        if(till_end_date_contract) :
            start_date = await self._convert_time_to_utc(datetime.now().today().replace(day=1, month=1, hour=0, minute=0, second=0, microsecond=0))
            end_date = await self._convert_time_to_utc(datetime.now().today().replace(day=end_contract_day+1, month=end_contract_month, hour=0, minute=0, second=0, microsecond=0))
        else :
            start_date = await self._convert_time_to_utc(datetime.now().today().replace(day=end_contract_day+1, month=end_contract_month, hour=0, minute=0, second=0, microsecond=0))
            end_date = await self._convert_time_to_utc(datetime.now().today().replace(day=1, month=1, year=dt.year + 1, hour=0, minute=0, second=0, microsecond=0))

        # _LOGGER.debug(self._till_end_date_contract)
        # _LOGGER.debug(
        #         f"start_date for entity {statistics_metadata_id} is {start_date}"
        #     )
        # _LOGGER.debug(
        #         f"end_date for entity {statistics_metadata_id} is {end_date}"
        #     )

        try:
            cursor = self._dbconnection.cursor()
            # _LOGGER.debug(f"SELECT MAX(state) - MIN(state) AS total_import FROM statistics WHERE metadata_id = '{statistics_metadata_id}' AND created >= datetime('{start_date}') AND created <= datetime('{end_date}');")
            cursor.execute(f"SELECT MAX(state) - MIN(state) AS total_import FROM statistics WHERE metadata_id = '{statistics_metadata_id}' AND created >= datetime('{start_date}') AND created <= datetime('{end_date}');")
            record = cursor.fetchone()
            # _LOGGER.debug(record)
            if(record == None):
                return 0
            else:
                return record[0]
        except Error as e:
            _LOGGER.error(e)
            raise Exception(e)

    # async def _get_first_recorded_state_in_month(self, entity_id: str, end_date_contract, till_end_date_contract):    
    #     dt = datetime.strptime(end_date_contract, '%Y-%m-%d')
    #     end_contract_month = dt.month
    #     end_contract_day = dt.day

    #     if(till_end_date_contract) :
    #         start_date = await self._convert_time_to_utc(datetime.now().today().replace(day=1, month=1, hour=0, minute=0, second=0, microsecond=0))
    #         end_date = await self._convert_time_to_utc(datetime.now().today().replace(day=end_contract_day+1, month=end_contract_month, hour=0, minute=0, second=0, microsecond=0))
    #     else :
    #         start_date = await self._convert_time_to_utc(datetime.now().today().replace(day=end_contract_day+1, month=end_contract_month, hour=0, minute=0, second=0, microsecond=0))
    #         end_date = await self._convert_time_to_utc(datetime.now().today().replace(day=1, month=1, year=dt.year + 1, hour=0, minute=0, second=0, microsecond=0))

    #     _LOGGER.debug(
    #             f"start_date for entity {entity_id} is {start_date}"
    #         )
    #     _LOGGER.debug(
    #             f"end_date for entity {entity_id} is {end_date}"
    #         )

    #     history_list = await get_instance(self.hass).async_add_executor_job(
    #         history.state_changes_during_period,
    #         self.hass,
    #         start_date,
    #         end_date,
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
    #         _LOGGER.warning(
    #             'Historical data not found for entity "%s". Total usage may be off.', entity_id
    #         )
    #         return None
    #     else:
    #         _LOGGER.warning(
    #             history_list
    #         )
    #         return history_list[entity_id][0]