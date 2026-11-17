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
## Buttons and switches (inputs only; START, STOP and RUN share lines with the Pi header).
set_property PACKAGE_PIN C14 [get_ports btn_start];   # SW5 START, RP_GPIO20
set_property PACKAGE_PIN B15 [get_ports btn_stop];    # SW4 STOP, RP_GPIO21
set_property PACKAGE_PIN C13 [get_ports btn_run];     # SW6 RUN, RP_GPIO16
set_property PACKAGE_PIN R4 [get_ports btn_psw];      # SW1, GPIO_PSW
set_property PACKAGE_PIN M4 [get_ports dip_sw];       # SW3, GPIO_DIPSW
set_property PACKAGE_PIN N1 [get_ports ws2812_dout];  # S7_LED0, LED1 (WS2812B)
set_property IOSTANDARD LVCMOS33 [get_ports {btn_start btn_stop btn_run btn_psw dip_sw ws2812_dout}];   # TODO: belum dikonfirmasi
set_false_path -from [get_ports {btn_start btn_stop btn_run btn_psw dip_sw}]
set_false_path -to [get_ports ws2812_dout]
