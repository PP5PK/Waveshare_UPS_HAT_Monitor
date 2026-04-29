import smbus
import os
import sys
import time

# Config Register (R/W)
_REG_CONFIG       = 0x00
_REG_SHUNTVOLTAGE = 0x01
_REG_BUSVOLTAGE   = 0x02
_REG_POWER        = 0x03
_REG_CURRENT      = 0x04
_REG_CALIBRATION  = 0x05


class BusVoltageRange:
    RANGE_16V = 0x00
    RANGE_32V = 0x01


class Gain:
    DIV_1_40MV  = 0x00
    DIV_2_80MV  = 0x01
    DIV_4_160MV = 0x02
    DIV_8_320MV = 0x03


class ADCResolution:
    ADCRES_9BIT_1S    = 0x00
    ADCRES_10BIT_1S   = 0x01
    ADCRES_11BIT_1S   = 0x02
    ADCRES_12BIT_1S   = 0x03
    ADCRES_12BIT_2S   = 0x09
    ADCRES_12BIT_4S   = 0x0A
    ADCRES_12BIT_8S   = 0x0B
    ADCRES_12BIT_16S  = 0x0C
    ADCRES_12BIT_32S  = 0x0D
    ADCRES_12BIT_64S  = 0x0E
    ADCRES_12BIT_128S = 0x0F


class Mode:
    POWERDOW             = 0x00
    SVOLT_TRIGGERED      = 0x01
    BVOLT_TRIGGERED      = 0x02
    SANDBVOLT_TRIGGERED  = 0x03
    ADCOFF               = 0x04
    SVOLT_CONTINUOUS     = 0x05
    BVOLT_CONTINUOUS     = 0x06
    SANDBVOLT_CONTINUOUS = 0x07


class INA219:
    def __init__(self, i2c_bus=1, addr=0x40):
        self.bus = smbus.SMBus(i2c_bus)
        self.addr = addr
        self._cal_value   = 0
        self._current_lsb = 0
        self._power_lsb   = 0
        self.set_calibration_16V_5A()

    def read(self, address):
        data = self.bus.read_i2c_block_data(self.addr, address, 2)
        return ((data[0] * 256) + data[1])

    def write(self, address, data):
        temp    = [0, 0]
        temp[1] = data & 0xFF
        temp[0] = (data & 0xFF00) >> 8
        self.bus.write_i2c_block_data(self.addr, address, temp)

    def set_calibration_16V_5A(self):
        self._current_lsb = 0.1524
        self._cal_value   = 26868
        self._power_lsb   = 0.003048
        self.write(_REG_CALIBRATION, self._cal_value)
        self.bus_voltage_range    = BusVoltageRange.RANGE_16V
        self.gain                 = Gain.DIV_2_80MV
        self.bus_adc_resolution   = ADCResolution.ADCRES_12BIT_32S
        self.shunt_adc_resolution = ADCResolution.ADCRES_12BIT_32S
        self.mode                 = Mode.SANDBVOLT_CONTINUOUS
        self.config = (self.bus_voltage_range    << 13 |
                       self.gain                 << 11 |
                       self.bus_adc_resolution   <<  7 |
                       self.shunt_adc_resolution <<  3 |
                       self.mode)
        self.write(_REG_CONFIG, self.config)

    def getShuntVoltage_mV(self):
        self.write(_REG_CALIBRATION, self._cal_value)
        value = self.read(_REG_SHUNTVOLTAGE)
        if value > 32767:
            value -= 65535
        return value * 0.01

    def getBusVoltage_V(self):
        self.write(_REG_CALIBRATION, self._cal_value)
        self.read(_REG_BUSVOLTAGE)
        return (self.read(_REG_BUSVOLTAGE) >> 3) * 0.004

    def getCurrent_mA(self):
        value = self.read(_REG_CURRENT)
        if value > 32767:
            value -= 65535
        return value * self._current_lsb

    def getPower_W(self):
        self.write(_REG_CALIBRATION, self._cal_value)
        value = self.read(_REG_POWER)
        if value > 32767:
            value -= 65535
        return value * self._power_lsb


# =============================================================================
# Display helpers
# =============================================================================

RESET = '\033[0m'
BOLD  = '\033[1m'
DIM   = '\033[2m'
AMBER = '\033[93m'  # amber  — primary values
BLUE  = '\033[94m'  # blue   — titles / charging
CYAN  = '\033[96m'  # cyan   — labels
GRAY  = '\033[90m'  # gray   — secondary elements
WHITE = '\033[97m'  # white

BOX_W = 35  # inner width (between border characters)


def _top():
    return GRAY + '╔' + '═' * BOX_W + '╗' + RESET


def _sep():
    return GRAY + '╠' + '═' * BOX_W + '╣' + RESET


def _bottom():
    return GRAY + '╚' + '═' * BOX_W + '╝' + RESET


def _border(content_ansi, content_len):
    """Wraps ANSI-formatted content between ║ borders, using
    content_len (without ANSI escapes) to calculate padding correctly."""
    padding = BOX_W - content_len
    return GRAY + '║' + RESET + content_ansi + ' ' * padding + GRAY + '║' + RESET


def _title(txt):
    inner = BOLD + BLUE + txt.center(BOX_W) + RESET
    return GRAY + '║' + RESET + inner + GRAY + '║' + RESET


def _row(label, value, color_l=CYAN, color_v=AMBER):
    """Row with label left-aligned and value right-aligned."""
    spaces      = BOX_W - 2 - len(label) - len(value) - 2
    content     = f'  {color_l}{label}{RESET}{" " * spaces}{color_v}{value}{RESET}  '
    content_len = 2 + len(label) + spaces + len(value) + 2
    return _border(content, content_len)


def _battery_bar(pct):
    """Row with a progress bar and percentage value."""
    bar_total = 22
    filled    = int(bar_total * pct / 100)
    empty     = bar_total - filled

    # Bold amber when critically low (<=20%), normal amber otherwise
    color_bar = AMBER if pct > 20 else BOLD + AMBER
    bar       = color_bar + '█' * filled + RESET + GRAY + '░' * empty + RESET
    pct_str   = f'{pct:5.1f}%'

    # inner layout: 2sp + bar(22) + 2sp + pct(6) + 3sp = 35
    content     = f'  {bar}  {AMBER}{pct_str}{RESET}   '
    content_len = 2 + bar_total + 2 + len(pct_str) + 3
    return _border(content, content_len)


# =============================================================================
# Main
# =============================================================================

if __name__ == '__main__':

    # -------------------------------------------------------------------------
    # Settings
    # -------------------------------------------------------------------------
    BATTERY_CAPACITY_MAH = 1000  # Total battery capacity in mAh — LiPo 803040 3.7V 1000mAh
    SHUTDOWN_THRESHOLD   = 10    # Battery % that triggers automatic shutdown
    SHUTDOWN_GRACE       = 7     # Consecutive readings below threshold before shutdown
    READ_INTERVAL        = 2     # Seconds between readings
    BLOCK_LINES          = 13    # Panel line count — update if fields are added
    # -------------------------------------------------------------------------

    ina219 = INA219(addr=0x43)
    first_run       = True
    shutdown_counter = 0

    while True:
        bus_voltage   = ina219.getBusVoltage_V()
        shunt_voltage = ina219.getShuntVoltage_mV() / 1000
        current       = ina219.getCurrent_mA()   # negative = discharging, positive = charging
        power         = ina219.getPower_W()

        p = (bus_voltage - 3) / 1.2 * 100
        if p > 100: p = 100
        if p < 0:   p = 0

        # --- Status ---
        on_battery = current < 0
        if on_battery:
            status_txt   = 'On battery'
            color_status = AMBER
        else:
            status_txt   = 'Charging'
            color_status = BLUE

        # --- Runtime estimate ---
        if on_battery and abs(current) > 1.0:
            remaining_h = (BATTERY_CAPACITY_MAH * (p / 100)) / abs(current)
            hours       = int(remaining_h)
            minutes     = int((remaining_h - hours) * 60)
            runtime_txt = f'{hours}h {minutes:02d}m'
        elif not on_battery:
            runtime_txt = '---'
        else:
            runtime_txt = '< 1 min'

        # --- Auto shutdown ---
        if p <= SHUTDOWN_THRESHOLD:
            shutdown_counter += 1
            if shutdown_counter >= SHUTDOWN_GRACE:
                sys.stdout.write('\n')
                print(f'{BOLD}{AMBER}!! Critical battery ({p:.1f}%) — shutting down...{RESET}')
                sys.stdout.flush()
                time.sleep(3)
                os.system('sudo systemctl poweroff')
                break
        else:
            shutdown_counter = 0

        # --- Reposition cursor to overwrite previous block ---
        if not first_run:
            sys.stdout.write(f'\033[{BLOCK_LINES}A')
        first_run = False

        # --- Render panel ---
        print(_top())
        print(_title(' Waveshare UPS HAT (C) Monitor '))
        print(_sep())
        print(_row('PSU Voltage',   f'{bus_voltage + shunt_voltage:6.3f} V'))
        print(_row('Shunt Voltage', f'{shunt_voltage:.6f} V'))
        print(_row('Load Voltage',  f'{bus_voltage:6.3f} V'))
        print(_row('Current',       f'{current / 1000:7.4f} A'))
        print(_row('Power',         f'{power:6.3f} W'))
        print(_sep())
        print(_battery_bar(p))

        # Status row: built manually to apply color only to the value
        spaces = BOX_W - 2 - len('Status') - len(status_txt) - 2
        print(_border(
            f'  {CYAN}Status{RESET}{" " * spaces}{color_status}{status_txt}{RESET}  ',
            2 + len('Status') + spaces + len(status_txt) + 2
        ))
        print(_row('Runtime', runtime_txt, color_v=CYAN))
        print(_bottom())

        sys.stdout.flush()
        time.sleep(READ_INTERVAL)
