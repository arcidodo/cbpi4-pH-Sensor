from cbpi.api import *
import smbus
import asyncio
import logging

logger = logging.getLogger(__name__)

@parameters([
    Property.Number("i2c_bus", default=1, description="I2C bus (meestal 1)"),
    Property.Text("i2c_address", default="0x48", description="ADS1115 I2C adres"),
    Property.Select("channel", options=["AIN0", "AIN1", "AIN2", "AIN3"], default="AIN1"),
    Property.Number("ph4_voltage", default=3.11, description="Gemeten spanning bij pH 4"),
    Property.Number("ph7_voltage", default=2.58, description="Gemeten spanning bij pH 7"),
    Property.Number("interval", default=2, description="Meet-interval (seconden)")
])
class PH_ADS1115(CBPiSensor):

    async def on_start(self):
        try:
            self.bus = smbus.SMBus(int(self.i2c_bus))
            self.address = int(self.i2c_address, 16)

            self.channel_map = {
                "AIN0": 0xC183,
                "AIN1": 0xD183,
                "AIN2": 0xE183,
                "AIN3": 0xF183,
            }

            logger.info("pH ADS1115 sensor gestart")

        except Exception as e:
            logger.error(f"I2C init fout: {e}")
            self.bus = None

    async def read_raw(self):
        if not self.bus:
            return None

        try:
            config = self.channel_map[self.channel]
            self.bus.write_i2c_block_data(
                self.address,
                0x01,
                [(config >> 8) & 0xFF, config & 0xFF]
            )

            await asyncio.sleep(0.1)

            data = self.bus.read_i2c_block_data(self.address, 0x00, 2)
            raw = (data[0] << 8) | data[1]

            if raw & 0x8000:
                raw -= 1 << 16

            return raw

        except Exception as e:
            logger.error(f"ADS1115 leesfout: {e}")
            return None

    def raw_to_voltage(self, raw):
        return raw * (4.096 / 32768.0)

    def voltage_to_ph(self, voltage):
        ph4 = float(self.ph4_voltage)
        ph7 = float(self.ph7_voltage)
        slope = (7.0 - 4.0) / (ph7 - ph4)
        return 4.0 + (voltage - ph4) * slope

    async def run(self):
        while self.running:
            raw = await self.read_raw()
            if raw is not None:
                voltage = self.raw_to_voltage(raw)
                ph = self.voltage_to_ph(voltage)
                self.value = round(ph, 2)

            await asyncio.sleep(int(self.interval))


def setup(cbpi):
    cbpi.plugin.register("PH_ADS1115", PH_ADS1115)
