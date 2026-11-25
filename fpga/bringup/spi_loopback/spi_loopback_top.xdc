## Bring-up with the Raspberry Pi 5: SPI0 CE0 loopback.  Pins from the official connection table (TK-1, TK-2;
## board/BOARD_INFO.md).  The I/O standards are an inference (ADR-024): bank 15 VCCO is not stated in the official
## documents.  Unlike the other bring-up designs this one drives a line shared with the Pi header (MISO, A7), and
## only while CE0 is low.  The table marks JP11 "(CUT)" on A8 (SCLK) and JP9 "(CUT)" on A6 (MOSI); whether these lines
## reach the FPGA is UNKNOWN until this test runs on the board.
set_property CFGBVS VCCO [current_design]
set_property CONFIG_VOLTAGE 3.3 [current_design]
set_property PACKAGE_PIN B13 [get_ports clk_in];   # CLK20M
set_property IOSTANDARD LVCMOS33 [get_ports clk_in];   # TODO: belum dikonfirmasi
create_clock -name clk_in -period 50.000 [get_ports clk_in]
set_property PACKAGE_PIN A8 [get_ports spi_sclk];   # RP_GPIO11 SPI0 SCLK, JP11(CUT)
set_property PACKAGE_PIN A6 [get_ports spi_mosi];   # RP_GPIO10 SPI0 MOSI, JP9(CUT)
set_property PACKAGE_PIN A7 [get_ports spi_miso];   # RP_GPIO9 SPI0 MISO
set_property PACKAGE_PIN D9 [get_ports spi_cs_n];   # RP_GPIO8 SPI0 CE0
set_property IOSTANDARD LVCMOS33 [get_ports {spi_sclk spi_mosi spi_miso spi_cs_n}];   # TODO: belum dikonfirmasi
set_property PACKAGE_PIN R3 [get_ports led1];   # GPIO_LED1, D5
set_property PACKAGE_PIN R2 [get_ports led2];   # GPIO_LED2, D6
set_property IOSTANDARD LVCMOS33 [get_ports {led1 led2}];   # TODO: belum dikonfirmasi
## The SPI inputs are asynchronous to CLK20M and go through two-flop synchronizers.
set_false_path -from [get_ports {spi_sclk spi_mosi spi_cs_n}]
set_false_path -to [get_ports {spi_miso led1 led2}]
