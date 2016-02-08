REG_CFG    = const(1)
REG_B_UP   = const(2)
REG_B_LOW  = const(3)
REG_B_CRIT = const(4)
REG_A_TEMP = const(5)
REG_M_ID   = const(6)
REG_D_ID   = const(7)
REG_T_RES  = const(8)

T_RES_MIN = const(0)
T_RES_LOW = const(1)
T_RES_AVG = const(2)
T_RES_MAX = const(3)

class MCP9808(object):
    def __init__(self, i2c=None, addr=0x18):
        assert i2c != None, 'No I2C object given!'
        self._i2c = i2c
        self._addr = addr
        self._check_device()

    def _send(self, buf):
        self._i2c.send(buf, self._addr)
        
    def _recv(self, n=2):
        return self._i2c.recv(n, self._addr)
    
    def _check_device(self):
        self._send(REG_M_ID)
        self._m_id = self._recv(2)
        if not self._m_id == b'\x00T':
            raise Exception("Invalid manufacturer ID: '%s'!" % self._m_id)
        self._send(REG_D_ID)
        self._d_id = self._recv(2)
        if not self._d_id == b'\x04\x00':
            raise Exception("Invalid device or revision ID: '%s'!" % self._d_id)
        
    # Set sensor into shutdown mode to draw less than 1 uA and disable 
    # continous temperature conversion. When not in shutdown mode the sensor
    # does draw 200-400 uA.
    def set_shutdown(self, shdn=True):        
        self._send(REG_CFG)
        cfg = self._recv(2)
        b = bytearray()
        b.append(REG_CFG)
        if shdn:
            b.append(cfg[0] | 1)
        else:
            b.append(cfg[0] & ~1)
        b.append(cfg[1])
        self._send(b)
        
    # Read temperature in degree celsius and return float value
    def read(self):
        self._send(REG_A_TEMP)
        raw = self._recv(2)
        u = (raw[0] & 0x0f) << 4
        l = raw[1] / 16
        if raw[0] & 0x10 == 0x10:
            temp = 256 - (u + l)
        else:
            temp = u + l
        return temp
    
    # Read a temperature in degree celsius and return a tuple of two parts.
    # The first part is the decimal patr and the second the fractional part 
    # of the value.
    # This method does avoid floating point arithmetic completely to support 
    # plattforms missing float support.
    def read_int(self):
        self._send(REG_A_TEMP)
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
        
    # Sets the temperature resolution. Higher resolutions do yield longer 
    # conversion times:
    #   Mode        Resolution  Conversion time
    # ------------------------------------------
    #   T_RES_MIN   0.5°C        30 ms
    #   T_RES_LOW   0.25°C       65 ms
    #   T_RES_AVG   0.125°C     130 ms
    #   T_RES_MAX   0.0625°C    250 ms
    #
    # On power up the mode is set to maximum resolution.
    def set_resolution(self, r):
        assert r in [0, 1, 2, 3], 'Invalid temperature resolution requested!'
        b = bytearray()
        b.append(REG_T_RES)
        b.append(r)
        self._send(b)