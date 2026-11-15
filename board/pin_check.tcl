# Ask Vivado's device database what each ZERO7 pin used by SENTINEL is on xc7s25csga225-1:
# bank, pin function and clock capability.  Pin numbers come from the official connection table
# (docs/official/ZERO7FPGA_Connection-table_261109_001.pdf); this script only checks them
# against the part, it does not prove anything about the board.
# Run from the repository root:
#   vivado -mode batch -nojournal -nolog -source board/pin_check.tcl
# Lines printed by this script start with PIN or CHECK.

set part xc7s25csga225-1
create_project -in_memory -part $part
set_property DESIGN_MODE PinPlanning [current_fileset]
open_io_design -name io_1

# pin  net name in the connection table
set pins {
    B13 CLK20M
    H1  EXT_CLK
    A8  RP_GPIO11_SCLK
    A6  RP_GPIO10_MOSI
    A7  RP_GPIO9_MISO
    D9  RP_GPIO8_CE0
    C10 RP_GPIO7_CE1
    C9  RP_GPIO25
    D8  RP_GPIO24
    C8  RP_GPIO23
    N1  S7_LED0
    D7  RP_GPIO18_LED2
    R3  GPIO_LED1
    R2  GPIO_LED2
    A10 RP_GPIO6_D3_BLUE
    B10 RP_GPIO13_D9_GREEN
    B11 RP_GPIO19_D8_RED
    R4  GPIO_PSW
    M4  GPIO_DIPSW
    C14 RP_GPIO20_SW5_START
    B15 RP_GPIO21_SW4_STOP
    C13 RP_GPIO16_SW6_RUN
    A11 AIN33_P
    A12 AIN33_N
    A13 AIN32_P
    A14 AIN32_N
    H14 QSPI_DQ0
    H15 QSPI_DQ1
    J12 QSPI_DQ2
    K13 QSPI_DQ3
    L11 QSPI_CS
    K11 PUDC_B
}
puts "CHECK part $part"
foreach {pin net} $pins {
    set obj [get_package_pins -quiet $pin]
    if {[llength $obj] == 0} {
        puts "PIN $pin $net NOT_FOUND"
        continue
    }
    set func [get_property PIN_FUNC $obj]
    set bank [get_property BANK $obj]
    set gclk ""
    foreach prop {IS_GLOBAL_CLK IS_CLK_CAPABLE IS_GENERAL_PURPOSE} {
        if {![catch {get_property $prop $obj} v]} { append gclk " $prop=$v" }
    }
    puts "PIN $pin $net bank=$bank func=$func$gclk"
}
puts "CHECK b13_properties_begin"
report_property [get_package_pins B13]
puts "CHECK b13_properties_end"
foreach bank {14 15 34} {
    set b [get_iobanks -quiet $bank]
    if {[llength $b]} {
        set line "CHECK iobank $bank"
        foreach prop {BANK_TYPE DCI_CASCADE INTERNAL_VREF} {
            if {![catch {get_property $prop $b} v]} { append line " $prop=$v" }
        }
        puts $line
    }
}
