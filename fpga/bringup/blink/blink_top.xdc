## Bring-up without the Raspberry Pi (ADR-026).  Pins from the official connection table (board/BOARD_INFO.md).
## The I/O standards are an inference (ADR-024): LVCMOS33 on banks 15 and 34.  Measure the bank voltages with
## vcco_probe first; bring-up designs drive only FPGA-only pins, so a different VCCO costs function, not hardware.
set_property CFGBVS VCCO [current_design]
set_property CONFIG_VOLTAGE 3.3 [current_design]
set_property PACKAGE_PIN B13 [get_ports clk_in];   # CLK20M
set_property IOSTANDARD LVCMOS33 [get_ports clk_in];   # TODO: belum dikonfirmasi
create_clock -name clk_in -period 50.000 [get_ports clk_in]
set_property PACKAGE_PIN R3 [get_ports led1];   # GPIO_LED1, D5
set_property PACKAGE_PIN R2 [get_ports led2];   # GPIO_LED2, D6
set_property IOSTANDARD LVCMOS33 [get_ports {led1 led2}];   # TODO: belum dikonfirmasi
set_false_path -to [get_ports {led1 led2}]
