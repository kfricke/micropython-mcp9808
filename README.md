# micropython-mcp9808
This repository contains a MicroPython "driver" implementation for the MCP9808
temperature sensor from Microchip.

## Implemented
* Reading the temperature value in degree celsius. The `get_temp()` method supports floating point values and the `get_temp_int()` method does not use floating point arythmetic at all and does return a tuple of decimal and fraction parts of the temperature reading.
* Shutdown mode to save power. When not in shutdown mode the sensor
does draw 200-400 uA. Data acquisition can only be stopped in the so called
"shutdown mode". In this mode communication is still possible using I2C.
* Changing the data acquisition resolution and duration. On power up the sensor
is set to maximum resolution.

    | Mode Name | Resolution  | Duration | Samples / sec |
    | --------- | ----------- | -------- | ------------- |
    | T_RES_MIN | +-0.5 °C    |    30 ms | 33            |
    | T_RES_LOW | +-0.25 °C   |    65 ms | 15            |
    | T_RES_AVG | +-0.125 °C  |   130 ms |  7            |
    | T_RES_MAX | +-0.0625 °C |   250 ms |  4            |
* Alert mode: boundaries are defined by using
`set_alert_boundary_temp()`. `set_alert_mode(self, enable_alert, output_mode, polarity, selector)`
allows to enable/disable alert functionality, set the desired output mode to
comparator or interrupt, switch te polarity between active-low or active-high
(pull-up resistor required!) as well as what boundaries should trigger an alert.

## Not yet implemented
* hysteresis
