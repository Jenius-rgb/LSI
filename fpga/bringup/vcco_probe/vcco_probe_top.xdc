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
## PMOD1 (J1) table pins 1-4 high and table pins 5-8 low; N1 (also J7) high.
## Pin numbers follow the official connection table; their physical position on J1 is [UNKNOWN]: check the silkscreen.
set_property PACKAGE_PIN D15 [get_ports {pmod1_hi[0]}];   # J1 pin 1
set_property PACKAGE_PIN E15 [get_ports {pmod1_hi[1]}];   # J1 pin 2
set_property PACKAGE_PIN F15 [get_ports {pmod1_hi[2]}];   # J1 pin 3
set_property PACKAGE_PIN G15 [get_ports {pmod1_hi[3]}];   # J1 pin 4
set_property PACKAGE_PIN E13 [get_ports {pmod1_lo[0]}];   # J1 table pin 5
set_property PACKAGE_PIN E14 [get_ports {pmod1_lo[1]}];   # J1 table pin 6
set_property PACKAGE_PIN F14 [get_ports {pmod1_lo[2]}];   # J1 table pin 7
set_property PACKAGE_PIN G14 [get_ports {pmod1_lo[3]}];   # J1 table pin 8
set_property PACKAGE_PIN N1 [get_ports ws2812_dout];   # S7_LED0, also J7
set_property IOSTANDARD LVCMOS33 [get_ports {pmod1_hi[*] pmod1_lo[*] ws2812_dout}];   # TODO: belum dikonfirmasi
set_false_path -to [get_ports {pmod1_hi[*] pmod1_lo[*] ws2812_dout}]
