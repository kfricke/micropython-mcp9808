from machine import I2C

R_CFG    = const(1)
R_B_UP   = const(2)
R_B_LOW  = const(3)
R_B_CRIT = const(4)
R_A_TEMP = const(5)
R_M_ID   = const(6)
R_D_ID   = const(7)
R_T_RES  = const(8)

T_RES_MIN = const(0)
T_RES_LOW = const(1)
T_RES_AVG = const(2)
T_RES_MAX = const(3)

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
        self._i2c.send(buf, self._addr)

    def _recv(self, n):
        """
        Read bytes from the sensor using I2C. The byte count must be specified
        as an argument.
        Returns a bytearray containing the result.
        """
        return self._i2c.recv(n, self._addr)

    def _check_device(self):
        """
        Tries to identify the manufacturer and device identifiers.
        """
        self._send(R_M_ID)
        self._m_id = self._recv(2)
        if not self._m_id == b'\x00T':
            raise Exception("Invalid manufacturer ID: '%s'!" % self._m_id)
        self._send(R_D_ID)
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
        self._send(R_CFG)
        cfg = self._recv(2)
        b = bytearray()
        b.append(R_CFG)
        if shdn:
            b.append(cfg[0] | 1)
        else:
            b.append(cfg[0] & ~1)
        b.append(cfg[1])
        self._send(b)

    def get_temp(self):
        """
        Read temperature in degree celsius and return float value.
        """
        self._send(R_A_TEMP)
        raw = self._recv(2)
        u = (raw[0] & 0x0f) << 4
        l = raw[1] / 16
        if raw[0] & 0x10 == 0x10:
            temp = 256 - (u + l)
        else:
            temp = u + l
        return temp

    def get_temp_int(self):
        """
        Read a temperature in degree celsius and return a tuple of two parts.
        The first part is the decimal patr and the second the fractional part
        of the value.
        This method does avoid floating point arithmetic completely to support
        plattforms missing float support.
        """
        self._send(R_A_TEMP)
        raw = self._recv(2)
        u = (raw[0] & 0xf) << 4
        l = raw[1] >> 4
        if raw[0] & 0x10 == 0x10:
            temp = 256 - (u + l)
            frac = 256 - (raw[1] & 0x0f) * 100 >> 4
        else:
            temp = u + l
            frac = (raw[1] & 0x0f) * 100 >> 4
        return temp, frac

    def set_resolution(self, r):
        """
        Sets the temperature resolution.
        """
        if r not in [T_RES_MIN, T_RES_LOW, T_RES_AVG, T_RES_MAX]:
            raise ValueError('Invalid temperature resolution requested!')
        b = bytearray()
        b.append(R_T_RES)
        b.append(r)
        self._send(b)
