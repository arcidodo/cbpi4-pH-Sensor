"""
CraftBeerPi 4 Plugin – PH4502C pH Sensor via ADS1115
---------------------------------------------------
Reads pH using ADS1115 + PH4502C module.
Supports:
  • Two‑point calibration (pH7 + pH4)
  • Automatic slope & offset correction
  • Background sensor polling

Place this file in:
  ~/craftbeerpi4/modules/ph4502c/__init__.py

Restart CBPi and activate the module.
"""

import asyncio
import logging
from cbpi.api import CBPiSensor, Parameters, Property, SensorState, cbpi

import board
import busio
from adafruit_ads1x15 import ads1x15
from adafruit_ads1x15.ads1115 import ADS1115
from adafruit_ads1x15.analog_in import AnalogIn

logger = logging.getLogger(__name__)

def measure_voltage(channel, samples=10):
    vals = []
    for _ in range(samples):
        vals.append(channel.voltage)
    vals.sort()
    filtered = vals[2:-2]
    return sum(filtered)/len(filtered)


def voltage_to_ph(voltage, V_pH7, slope, offset):
    return 7 + (voltage - V_pH7) / slope + offset


@cbpi.sensor
class PH4502C_Sensor(CBPiSensor):
    name = "PH4502C via ADS1115"

    channel: int = Property.Number("ADS1115 Channel (0-3)", configurable=True, default_value=0)
    vp7: float = Property.Number("Calibration Voltage pH7", configurable=True, default_value=2.597)
    vp4: float = Property.Number("Calibration Voltage pH4", configurable=True, default_value=3.093)
    offset: float = Property.Number("Extra pH Offset", configurable=True, default_value=0.0)
    interval: int = Property.Number("Poll Interval (sec)", configurable=True, default_value=5)

    async def init(self):
        logger.info("Initializing PH4502C Sensor")

        # Init ADS1115
        i2c = busio.I2C(board.SCL, board.SDA)
        self.ads = ADS1115(i2c)
        self.ads.gain = 1

        ads_pins = [ads1x15.Pin.A0, ads1x15.Pin.A1, ads1x15.Pin.A2, ads1x15.Pin.A3]
        self.channel_obj = AnalogIn(self.ads, ads_pins[int(self.channel)])

        # Compute slope
        self.slope = (self.vp4 - self.vp7) / (4 - 7)
        logger.info(f"Slope: {self.slope:.4f} V/pH")

        self.task = asyncio.create_task(self.run())

    async def run(self):
        while True:
            voltage = measure_voltage(self.channel_obj)
            ph = voltage_to_ph(voltage, self.vp7, self.slope, self.offset)

            await self.push_state(SensorState(value=round(ph, 2)))

            logger.debug(f"Voltage: {voltage:.3f} V → pH: {ph:.2f}")

            await asyncio.sleep(self.interval)

    async def stop(self):
        logger.info("Stopping PH4502C sensor task")
        self.task.cancel()
