from __future__ import annotations
"""
Sensor component for GasWaterLicht
Author: Mike Vosters
"""

import asyncio
from datetime import timedelta, datetime
import logging
from typing import Any
from _sha1 import sha1
import async_timeout
import pytz
from homeassistant.core import HomeAssistant
from homeassistant.helpers.typing import ConfigType, DiscoveryInfoType
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.components.sensor import (
    RestoreSensor,
    SensorDeviceClass,
    STATE_CLASS_MEASUREMENT
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.util import Throttle
from homeassistant.components.recorder import get_instance, history
import sqlite3
from sqlite3 import Error
from .const.const import (
    ATTR_FRIENDLY_NAME,
    ATTR_THIS_MONTH_CAP,
    ATTR_THIS_MONTH_COSTS,
    ATTR_UNIT_OF_MEASUREMENT,
    CONF_SOURCES_TOTAL_GAS,
    CONF_SOURCES_TOTAL_POWER,
    CONF_SOURCES_TOTAL_SOLAR,
    CONF_END_DATE_CONTRACT,
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
from homeassistant.helpers.update_coordinator import (
    CoordinatorEntity,
    DataUpdateCoordinator,
    UpdateFailed,
)
from .GasWaterLichtResterend import GasWaterLichtResterendSensor
from .GasWaterLichtTotaal import GasWaterLichtTotaalSensor
from .GasWaterLichtPlafond import GasWaterLichtPlafondSensor
from .GasWaterLichtSensor import GasWaterLichtSensor
from .GasWaterLichtPrediction import GasWaterLichtPredictionSensor
from .GasWaterLichtPredictionTotal import GasWaterLichtPredictionTotalSensor

_LOGGER = logging.getLogger(__name__)

SCAN_INTERVAL = UPDATE_MIN_TIME

async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback
) -> None:
    _LOGGER.debug("Async setup GasWaterLicht")

    async_add_entities(
        [
            GasWaterLichtSensor(
                hass,
                "power",
                'Power usage this month',
                config_entry.data.get(CONF_SOURCES_TOTAL_POWER),
                config_entry.data.get(CONF_SOURCES_TOTAL_SOLAR)
            ),

            GasWaterLichtSensor(
                hass,
                "gas",
                'Gas usage this month',
                config_entry.data.get(CONF_SOURCES_TOTAL_GAS)
            ),

            # Resterend
            GasWaterLichtResterendSensor(
                hass,
                "power",
                'Prijsplafond stroom resterend tot contract',
                f"sensor.{DOMAIN}_rest_till_contract_power",
                config_entry.data.get(CONF_END_DATE_CONTRACT),
                True,
                config_entry.data.get(CONF_SOURCES_TOTAL_POWER),
                config_entry.data.get(CONF_SOURCES_TOTAL_SOLAR),
            ),

            GasWaterLichtResterendSensor(
                hass,
                "gas",
                'Prijsplafond gas resterend tot contract',
                f"sensor.{DOMAIN}_rest_till_contract_gas",
                config_entry.data.get(CONF_END_DATE_CONTRACT),
                True,
                config_entry.data.get(CONF_SOURCES_TOTAL_GAS)
            ),

            GasWaterLichtResterendSensor(
                hass,
                "power",
                'Prijsplafond stroom resterend vanaf contract',
                f"sensor.{DOMAIN}_rest_from_contract_power",
                config_entry.data.get(CONF_END_DATE_CONTRACT),
                False,
                config_entry.data.get(CONF_SOURCES_TOTAL_POWER),
                config_entry.data.get(CONF_SOURCES_TOTAL_SOLAR),
            ),

            GasWaterLichtResterendSensor(
                hass,
                "gas",
                'Prijsplafond gas resterend vanaf contract',
                f"sensor.{DOMAIN}_rest_from_contract_gas",
                config_entry.data.get(CONF_END_DATE_CONTRACT),
                False,
                config_entry.data.get(CONF_SOURCES_TOTAL_GAS)
            ),
            # Totaal
            GasWaterLichtTotaalSensor(
                hass,
                "gas",
                'Gas tot contract',
                f"sensor.{DOMAIN}_gas_to_contract",
                config_entry.data.get(CONF_END_DATE_CONTRACT),
                True,
                config_entry.data.get(CONF_SOURCES_TOTAL_GAS)
            ),
            GasWaterLichtTotaalSensor(
                hass,
                "power",
                'Stroom tot contract',
                f"sensor.{DOMAIN}_power_to_contract",
                config_entry.data.get(CONF_END_DATE_CONTRACT),
                True,
                config_entry.data.get(CONF_SOURCES_TOTAL_POWER),
                config_entry.data.get(CONF_SOURCES_TOTAL_SOLAR),
            ),
            GasWaterLichtTotaalSensor(
                hass,
                "gas",
                'Gas vanaf contract',
                f"sensor.{DOMAIN}_gas_since_contract",
                config_entry.data.get(CONF_END_DATE_CONTRACT),
                False,
                config_entry.data.get(CONF_SOURCES_TOTAL_GAS)
            ),
            GasWaterLichtTotaalSensor(
                hass,
                "power",
                'Stroom vanaf contract',
                f"sensor.{DOMAIN}_power_since_contract",
                config_entry.data.get(CONF_END_DATE_CONTRACT),
                False,
                config_entry.data.get(CONF_SOURCES_TOTAL_POWER),
                config_entry.data.get(CONF_SOURCES_TOTAL_SOLAR),
            ),
            # plafond
            GasWaterLichtPlafondSensor(
                hass,
                "gas",
                'Gas plafond tot contract',
                f"sensor.{DOMAIN}_ceiling_gas_to_contract",
                config_entry.data.get(CONF_END_DATE_CONTRACT),
                True,
                config_entry.data.get(CONF_SOURCES_TOTAL_GAS)
            ),
            GasWaterLichtPlafondSensor(
                hass,
                "power",
                'Stroom plafond tot contract',
                f"sensor.{DOMAIN}_ceiling_power_to_contract",
                config_entry.data.get(CONF_END_DATE_CONTRACT),
                True,
                config_entry.data.get(CONF_SOURCES_TOTAL_POWER),
                config_entry.data.get(CONF_SOURCES_TOTAL_SOLAR),
            ),
            GasWaterLichtPlafondSensor(
                hass,
                "gas",
                'Gas plafond vanaf contract',
                f"sensor.{DOMAIN}_ceiling_gas_since_contract",
                config_entry.data.get(CONF_END_DATE_CONTRACT),
                False,
                config_entry.data.get(CONF_SOURCES_TOTAL_GAS)
            ),
            GasWaterLichtPlafondSensor(
                hass,
                "power",
                'Stroom plafond vanaf contract',
                f"sensor.{DOMAIN}_ceiling_power_since_contract",
                config_entry.data.get(CONF_END_DATE_CONTRACT),
                False,
                config_entry.data.get(CONF_SOURCES_TOTAL_POWER),
                config_entry.data.get(CONF_SOURCES_TOTAL_SOLAR),
            ),
            GasWaterLichtPredictionSensor(
                hass,
                "gas",
                'Voorspelde gas deze maand',
                f"sensor.{DOMAIN}_predication_gas",
                config_entry.data.get(CONF_END_DATE_CONTRACT),
                False,
                config_entry.data.get(CONF_SOURCES_TOTAL_GAS)
            ),
            GasWaterLichtPredictionSensor(
                hass,
                "power",
                'Voorspelde stroom deze maand',
                f"sensor.{DOMAIN}_predication_power",
                config_entry.data.get(CONF_END_DATE_CONTRACT),
                False,
                config_entry.data.get(CONF_SOURCES_TOTAL_POWER),
                config_entry.data.get(CONF_SOURCES_TOTAL_SOLAR),
            ),
            GasWaterLichtPredictionTotalSensor(
                hass,
                "powqer",
                'Voorspelde stroom deze maand min teruglevering',
                f"sensor.{DOMAIN}_predication_power_minus_return",
                config_entry.data.get(CONF_END_DATE_CONTRACT),
                False,
                config_entry.data.get(CONF_SOURCES_TOTAL_POWER),
                config_entry.data.get(CONF_SOURCES_TOTAL_SOLAR),
            ),
        ]
    , update_before_add=True)


async def async_setup_platform(
    hass: HomeAssistant, 
    config: ConfigType, 
    async_add_entities: AddEntitiesCallback, 
    discovery_info: DiscoveryInfoType | None = None,
) -> None:
    if discovery_info is None:
        _LOGGER.error(
            "This platform is not available to configure "
            "from 'sensor:' in configuration.yaml"
        )
        return