## ZERO7 constraints for SENTINEL, part xc7s25csga225-1.
##
## Pin locations come from docs/official/ZERO7FPGA_Connection-table_261109_001.pdf [OFFICIAL].
## The official Zero7.xdc named in docs/official/Initialize_20260618_EN.pdf (slides 19 and 31)
## has not been published.  When it is, take the I/O standards from it and delete the TODO marks.
##
## Every IOSTANDARD below is marked "TODO: belum dikonfirmasi".  No official document states
## the VCCO voltage of banks 14, 15 and 34.  LVCMOS33 is an [INFERENCE] from the comment
## "Clock (20MHz, 3.3V)" visible in the Zero7.xdc screenshot (slide 31) and from the 3.3 V
## GPIO of the Raspberry Pi wired straight to these banks.  Do not program a board with a
## bitstream built from this file until the I/O standards are confirmed.
##
## Never place user logic on configuration pins: QSPI (F5, H14, H15, J12, K13, L11),
## JTAG (E5, K4, K5, L4), PROG (J5), INIT (L5), DONE (G5), MODE (M5, N5, M6), PUDC_B (K11).

## Configuration bank voltage.  CFGBVS and VCCO_0 (E6, P5) are tied to VCC3V3 in the
## connection table, pages 2, 3 and 6 [OFFICIAL].
set_property CFGBVS VCCO [current_design]
set_property CONFIG_VOLTAGE 3.3 [current_design]

## Clock.  Net CLK20M from X1 on B13 (connection table page 1).  B13 is IO_L13P_T2_MRCC_15,
## a clock-capable pin (results/vivado/pin_check.txt).  20 MHz per the Zero7.xdc comment.
set_property PACKAGE_PIN B13 [get_ports clk_in]
set_property IOSTANDARD LVCMOS33 [get_ports clk_in];                                 # TODO: belum dikonfirmasi
create_clock -name clk_in -period 50.000 [get_ports clk_in]

## SPI0 of the Raspberry Pi (connection table pages 1 and 2; GPIO functions per slide 59).
set_property PACKAGE_PIN A8 [get_ports spi_sclk];                                    # RP_GPIO11, SCLK
set_property PACKAGE_PIN D9 [get_ports spi_cs_n];                                    # RP_GPIO8, CE0
set_property PACKAGE_PIN A6 [get_ports spi_mosi];                                    # RP_GPIO10, MOSI
set_property PACKAGE_PIN A7 [get_ports spi_miso];                                    # RP_GPIO9, MISO
set_property IOSTANDARD LVCMOS33 [get_ports {spi_sclk spi_cs_n spi_mosi spi_miso}];  # TODO: belum dikonfirmasi

## Plain LEDs.  D5 and D6 belong to the FPGA alone.  D9 (green) and D8 (red) share their
## line with RP_GPIO13 and RP_GPIO19: the Raspberry Pi must leave those two GPIOs as inputs.
set_property PACKAGE_PIN R3  [get_ports {led[0]}];                                   # GPIO_LED1, D5
set_property PACKAGE_PIN R2  [get_ports {led[1]}];                                   # GPIO_LED2, D6
set_property PACKAGE_PIN B10 [get_ports {led[2]}];                                   # RP_GPIO13, D9 green
set_property PACKAGE_PIN B11 [get_ports {led[3]}];                                   # RP_GPIO19, D8 red
set_property IOSTANDARD LVCMOS33 [get_ports {led[*]}];                               # TODO: belum dikonfirmasi

## The SPI pins are sampled by synchronisers in clk_safe and the LEDs are slow status
## outputs, so none of these ports has a timing relationship with a clock.
set_false_path -from [get_ports {spi_sclk spi_cs_n spi_mosi}]
set_false_path -to   [get_ports {spi_miso led[*]}]

## Pins reserved for ports that top_board does not have yet.  Uncomment together with the
## RTL change (see docs/DECISIONS.md).
# set_property PACKAGE_PIN N1  [get_ports ws2812_dout];   # S7_LED0, LED1 (WS2812B), also J7
# set_property PACKAGE_PIN C9  [get_ports irq_done];      # RP_GPIO25
# set_property PACKAGE_PIN C14 [get_ports btn_start];     # SW5 START, shared with RP_GPIO20
# set_property PACKAGE_PIN B15 [get_ports btn_stop];      # SW4 STOP,  shared with RP_GPIO21
# set_property PACKAGE_PIN C13 [get_ports btn_run];       # SW6 RUN,   shared with RP_GPIO16
# set_property PACKAGE_PIN R4  [get_ports btn_psw];       # SW1, GPIO_PSW
# set_property PACKAGE_PIN M4  [get_ports dip_sw];        # SW3, GPIO_DIPSW
