## ZERO7 without the Raspberry Pi, PC as host over JTAG (ADR-025, ADR-026).  Pins from the official
## connection table; I/O standards are an inference (ADR-024).  Only FPGA-only pins are used.
set_property CFGBVS VCCO [current_design]
set_property CONFIG_VOLTAGE 3.3 [current_design]
set_property PACKAGE_PIN B13 [get_ports clk_in];   # CLK20M
set_property IOSTANDARD LVCMOS33 [get_ports clk_in];   # TODO: belum dikonfirmasi
create_clock -name clk_in -period 50.000 [get_ports clk_in]
set_property PACKAGE_PIN R3 [get_ports led_busy];    # GPIO_LED1, D5
set_property PACKAGE_PIN R2 [get_ports led_fatal];   # GPIO_LED2, D6
set_property PACKAGE_PIN N1 [get_ports ws2812_dout]; # S7_LED0, LED1 (WS2812B)
set_property IOSTANDARD LVCMOS33 [get_ports {led_busy led_fatal ws2812_dout}];   # TODO: belum dikonfirmasi
set_false_path -to [get_ports {led_busy led_fatal ws2812_dout}]
