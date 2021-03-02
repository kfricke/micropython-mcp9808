# Imports
from machine import I2C


# Register pointers
REG_CONFIG = const(1)
REG_TEMP_BOUNDARY_UPPER = const(2)
REG_TEMP_BOUNDARY_LOWER = const(3)
REG_TEMP_BOUNDARY_CRITICAL = const(4)
REG_TEMP = const(5)
REG_MANUFACTURER_ID = const(6)
REG_DEVIDE_ID = const(7)
REG_RESOLUTION = const(8)


# Sensor resolution values
TEMP_RESOLUTION_MIN = const(0) # +0.5 C, refresh rate 30 ms
TEMP_RESOLUTION_LOW = const(1) # +0.25 C, refresh rate 65 ms
TEMP_RESOLUTION_AVG = const(2) # +0.125 C, refresh rate 130 ms
TEMP_RESOLUTION_MAX = const(3) # +0.0625 C, refresh rate 250 ms [Default]


# Alert selectors
ALERT_SELECT_ALL = const(0) # ambient > upper || ambient > critical || ambient < lower [Default]
ALERT_SELECT_CRIT = const(1) # Ambient temp > critical


# Alert polarity
ALERT_POLARITY_ALOW = const(0) # Active-low, requires pull-up [Default]
ALERT_POLARITY_AHIGH = const(1) # Active-high


# Alert output mode
ALERT_OUTPUT_COMPARATOR = const(0)
ALERT_OUTPUT_INTERRUPT = const(1)

class MCP9808(object):
    """
    This class implements an interface to the MCP9808 temprature sensor from
    Microchip.
    """

    def __init__(self, i2c=None, addr=0x18):
        """
        Initialize a sensor object on the given I2C bus and accessed by the
        given address.
        """
        if i2c == None or i2c.__class__ != I2C:
            raise ValueError('I2C object needed as argument!')
        self._i2c = i2c
        self._addr = addr
        self._check_device()

    def _send(self, buf):
        """
        Sends the given bufer object over I2C to the sensor.
        """
        if hasattr(self._i2c, "writeto"):
            # Micropython
            self._i2c.writeto(self._addr, buf)
        elif hasattr(self._i2c, "send"):
            # PyBoard Micropython
            self._i2c.send(self._addr, buf)
        else:
            raise Exception("Invalid I2C object. Unknown Micropython/platform?")

    def _recv(self, n):
        """
        Read bytes from the sensor using I2C. The byte count must be specified
        as an argument.
        Returns a bytearray containing the result.
        """
        if hasattr(self._i2c, "writeto"):
            # Micropython (PyCom)
            return self._i2c.readfrom(self._addr, n)
        elif hasattr(self._i2c, "send"):
            # PyBoard Micropython
            return self._i2c.recv(n, self._addr)
        else:
            raise Exception("Invalid I2C object. Unknown Micropython/platform?")

    def _check_device(self):
        """
        Tries to identify the manufacturer and device identifiers.
        """
        self._send(REG_MANUFACTURER_ID)
        self._m_id = self._recv(2)
        if not self._m_id == b'\x00T':
            raise Exception("Invalid manufacturer ID: '%s'!" % self._m_id)
        self._send(REG_DEVIDE_ID)
        self._d_id = self._recv(2)
        if not self._d_id == b'\x04\x00':
            raise Exception("Invalid device or revision ID: '%s'!" % self._d_id)

    def set_shutdown_mode(self, shdn=True):
        """
        Set sensor into shutdown mode to draw less than 1 uA and disable
        continous temperature conversion.
        """
        if shdn.__class__ != bool:
            raise ValueError('Boolean argument needed to set shutdown mode!')
        self._send(REG_CONFIG)
        cfg = self._recv(2)
        b = bytearray()
        b.append(REG_CONFIG)
        if shdn:
            b.append(cfg[0] | 1)
        else:
            b.append(cfg[0] & ~1)
        b.append(cfg[1])
        self._send(b)

    def set_alert_mode(self, enable_alert=True, output_mode=ALERT_OUTPUT_INTERRUPT, polarity=ALERT_POLARITY_ALOW, selector=ALERT_SELECT_ALL):
        """
        Set sensor into alert mode with the provided output,
        polarity and selector parameters

        If output mode is set to interrupt, a call to acknowledge_alert_irq()
        is required to deassert the MCP9808
        """
        if enable_alert.__class__ != bool:
            raise ValueError('Boolean argument needed to set alert mode!')
        if output_mode not in [ALERT_OUTPUT_COMPARATOR, ALERT_OUTPUT_INTERRUPT]:
            raise ValueError("Invalid output mode set.")
        if selector not in [ALERT_SELECT_ALL, ALERT_SELECT_CRIT]:
            raise ValueError("Invalid alert selector set.")
        if polarity not in [ALERT_POLARITY_ALOW, ALERT_POLARITY_AHIGH]:
            raise ValueError("Invalid alert polarity set.")
        
        enable_alert = 1 if enable_alert else 0 
        self._send(REG_CONFIG)
        cfg = self._recv(2)

        alert_bits = (output_mode | (polarity << 1) | (selector << 2) | (enable_alert << 3)) & 0xF
        lsb_data = (cfg[1] & 0xF0) | alert_bits

        b = bytearray()
        b.append(REG_CONFIG)
        b.append(cfg[0])
        b.append(lsb_data)
        self._send(b)

    def acknowledge_alert_irq(self):
        """
        Must be called if MCP9808 is operating in interrupt output mode
        """
        self._send(REG_CONFIG)
        cfg = self._recv(2)
        b = bytearray()
        b.append(REG_CONFIG)
        b.append(cfg[0]) # MSB data
        b.append(cfg[1] | 0x20) # LSB data with interrupt clear bit set
        self._send(b)  

    def set_alert_boundary_temp(self, boundary_register, value):
        """
        Sets the alert boundary for the requested boundary register
        """
        if boundary_register not in [REG_TEMP_BOUNDARY_LOWER, REG_TEMP_BOUNDARY_UPPER, REG_TEMP_BOUNDARY_CRITICAL]:
            raise ValueError("Given alert boundary register is not valid!")
        if value < -128 or value > 127: # 8 bit two's complement
            raise ValueError("Temperature out of range [-128, 127]")

        integral = int(value)
        frac = abs(value - integral)
        if integral < 0:
            integral = (1 << 9) + integral
        integral = ((integral & 0x1FF) << 4) 
        frac = (((1 if frac * 2 >= 1 else 0) << 1) + (1 if (frac * 2 - int(frac * 2)) * 2 >= 1 else 0)) << 2
        twos_value = (integral + frac if value >= 0 else integral - frac) & 0x1ffc 
        b = bytearray()
        b.append(boundary_register)
        b.append((twos_value & 0xFF00) >> 8)
        b.append(twos_value & 0xFF)
        self._send(b)
        

    def set_resolution(self, r):
        """
        Sets the temperature resolution.
        """
        if r not in [TEMP_RESOLUTION_MIN, TEMP_RESOLUTION_LOW, TEMP_RESOLUTION_AVG, TEMP_RESOLUTION_MAX]:
            raise ValueError('Invalid temperature resolution requested!')
        b = bytearray()
        b.append(REG_RESOLUTION)
        b.append(r)
        self._send(b)

    def get_temp(self):
        """
        Read temperature in degree celsius and return float value.
        """
        self._send(REG_TEMP)
        raw = self._recv(2)
        u = (raw[0] & 0x0f) << 4
        l = raw[1] / 16
        if raw[0] & 0x10 == 0x10:
            temp = (u + l) - 256
        else:
            temp = u + l
        return temp

    def get_temp_int(self):
        """
        Read a temperature in degree celsius and return a tuple of two parts.
        The first part is the decimal part and the second the fractional part
        of the value.
        This method does avoid floating point arithmetic completely to support
        platforms missing float support.
        """
        self._send(REG_TEMP)
        raw = self._recv(2)
        u = (raw[0] & 0xf) << 4
        l = raw[1] >> 4
        if raw[0] & 0x10 == 0x10:
            temp = (u + l) - 256
            frac = -((raw[1] & 0x0f) * 100 >> 4)
        else:
            temp = u + l
            frac = (raw[1] & 0x0f) * 100 >> 4
        return temp, frac

    def _debug_config(self, cfg=None):
        """
        Prints the first 9 bits of the config register mapped to human
        readable descriptions
        """
        if not cfg:
            self._send(REG_CONFIG)
            cfg = self._recv(2)
        
        # meanings[a][b] with a the bit index (LSB order),
        # b=0 the config description and b={bit value}+1 the value description 
        meanings = [
            ["Alert output mode", "Comparator", "Interrupt"],
            ["Alert polarity", "Active-low", "Active-high"],
            ["Alert Selector", "All", "Only Critical"],
            ["Alert enabled", "False", "True"],
            ["Alert status", "Not asserted", "Asserted as set by mode"],
            ["Interrupt clear bit", "0", "1"],
            ["Window [low, high] locked", "Unlocked", "Locked"],
            ["Critical locked", "Unlocked", "Locked"],
            ["Shutdown", "False", "True"]
        ]

        print("Raw config: {}".format(str(cfg)))
        for i in range(0, min(len(meanings), len(cfg)*8)):
            part = 0 if i > 7 else 1
            value = 1 if (cfg[part] & (2**(i % 8))) > 0 else 0
            print(meanings[i][0] + ": " + meanings[i][1 + value])