# Check that this Vivado installation matches the contest requirements:
# version 2025.2 and the official part xc7s25csga225-1 (docs/official/GUIDE_LSI_2027_FINALE.pdf, page 5).
# Run from the repository root:
#   vivado -mode batch -nojournal -nolog -source tools/vivado_check_part.tcl
# Every line this script prints starts with CHECK so it can be filtered from the Vivado banner.

set part xc7s25csga225-1
puts "CHECK vivado_version [version -short]"
puts "CHECK part_query $part"
set found [get_parts -quiet $part]
puts "CHECK part_found [llength $found]"
if {[llength $found] > 0} {
    foreach prop {FAMILY DEVICE PACKAGE SPEED TEMPERATURE_GRADE_LETTER LUT_ELEMENTS FLIPFLOPS SLICES BLOCK_RAMS DSP
                  MMCM PLL IO_PIN_COUNT AVAILABLE_IOBS REF_OPERATING_VOLTAGE MIN_OPERATING_TEMPERATURE MAX_OPERATING_TEMPERATURE} {
        if {[catch {get_property $prop $found} value]} {
            puts "CHECK part_property $prop (not available)"
        } else {
            puts "CHECK part_property $prop $value"
        }
    }
}
puts "CHECK spartan7_parts_installed [llength [get_parts -quiet xc7s*]]"
puts "CHECK zynq7000_parts_installed [llength [get_parts -quiet xc7z*]]"
if {[llength $found] > 0 && [version -short] eq "2025.2"} {
    puts "CHECK status CUKUP"
} elseif {[llength $found] == 0} {
    puts "CHECK status PERLU_KONFIGURASI"
} else {
    puts "CHECK status FATAL_VERSION"
}
