# Official synthesis and implementation of the complete design on the contest chip (ADR-014).
# The organisers require a synthesis report for AMD Spartan-7 XC7S25CSGA225-1 from every team
# (docs/official/README.md).  This script builds top_board with board/zero7.xdc and keeps the
# standard Vivado reports after synthesis and after implementation.  It does not write a
# bitstream: the I/O standards of the board are not confirmed yet (board/BOARD_INFO.md).
#
# Run through fpga/run_official.py (python tools/run.py synth-official), which passes:
#   vivado -mode batch -source fpga/synth_official.tcl -tclargs <outdir> <K> <lane_impl> <c3>
#          <weight_aw> <act0_aw> <act1_aw> <safe_div> [<turbo_mhz>]
# The optional turbo_mhz (side runs only) analyses clk_fast_turbo at that frequency instead of
# turbo level 0 (= clk_safe), to check how far the lane domain meets static timing.

if { $argc != 8 && $argc != 9 } {
    puts "usage: synth_official.tcl outdir K lane_impl c3 weight_aw act0_aw act1_aw safe_div ?turbo_mhz?"
    exit 2
}
lassign $argv outdir k impl c3 weight_aw act0_aw act1_aw safe_div turbo_arg
set part xc7s25csga225-1
set top top_board
file mkdir $outdir

set root [file normalize [file join [file dirname [info script]] ..]]
set sources {
    rtl/lane_lut.v rtl/lane_dsp_min.v rtl/lane_dsp_full.v rtl/lane_array.v rtl/lane_checker.v
    rtl/ram_tdp.v rtl/sum_tree.v rtl/wc_gen.v rtl/operand_gen.v rtl/postproc.v rtl/pool.v
    rtl/counter_bank.v rtl/cdc_fifo.v rtl/platform/xilinx/cdc_fifo_xpm.v rtl/fast_path.v rtl/engine.v
    rtl/spi_slave.v rtl/regfile.v rtl/governor.v rtl/clk_seq.v rtl/clk_gen.v
    rtl/clkwiz_seq.v rtl/platform/xilinx/clk_gen_xilinx.v rtl/xadc_temp.v rtl/platform/xilinx/xadc_prim_xilinx.v rtl/ws2812_tx.v rtl/status_led.v rtl/top_core.v board/top_board.v
}
set_part $part
set_property XPM_LIBRARIES {XPM_CDC XPM_MEMORY XPM_FIFO} [current_project]
foreach f $sources { read_verilog [file join $root $f] }
read_xdc [file join $root board/zero7.xdc]

# MMCM2 inside a Clocking Wizard v6.0 with AXI4-Lite dynamic reconfiguration (ADR-023, PG065).
# Level 0 of the turbo table equals clk_safe; the IP is regenerated on every run.
set ipdir [file join $root build ip_[file tail $outdir]]
file delete -force $ipdir
file mkdir $ipdir
create_ip -name clk_wiz -vendor xilinx.com -library ip -module_name clk_wiz_turbo -dir $ipdir
if { $turbo_arg ne "" } { set turbo_mhz [format %.3f $turbo_arg] } else { set turbo_mhz [format %.3f [expr {1000.0 / $safe_div}]] }
set_property -dict [list CONFIG.PRIM_IN_FREQ {20.000} CONFIG.PRIM_SOURCE {No_buffer} CONFIG.USE_DYN_RECONFIG {true} CONFIG.INTERFACE_SELECTION {Enable_AXI} CONFIG.CLKOUT1_REQUESTED_OUT_FREQ $turbo_mhz CONFIG.USE_LOCKED {true}] [get_ips clk_wiz_turbo]
set_property GENERATE_SYNTH_CHECKPOINT false [get_files clk_wiz_turbo.xci]
generate_target {synthesis} [get_ips clk_wiz_turbo]
puts "TIMING turbo_ip M [get_property CONFIG.MMCM_CLKFBOUT_MULT_F [get_ips clk_wiz_turbo]] D [get_property CONFIG.MMCM_DIVCLK_DIVIDE [get_ips clk_wiz_turbo]] O [get_property CONFIG.MMCM_CLKOUT0_DIVIDE_F [get_ips clk_wiz_turbo]]"

set wc [exec python -c "import sys; sys.path.insert(0, r'$root/tools'); from sim import wc_widths; print(*wc_widths($k))"]
lassign $wc wc1 wc2 wc3
if {$k != 8 && ($wc1 != 11 || $wc2 != 14 || $wc3 != 16)} {
    puts "ERROR: top_board keeps the checksum weight widths of K = 8; K = $k needs $wc1/$wc2/$wc3"
    exit 2
}

synth_design -top $top -part $part -include_dirs [list [file join $root rtl/gen]] \
    -verilog_define SENTINEL_XILINX=1 -verilog_define SENTINEL_SAFE_DIV=$safe_div \
    -generic K=$k -generic LANE_IMPL=$impl -generic C3_EN=$c3 \
    -generic WEIGHT_AW=$weight_aw -generic ACT0_AW=$act0_aw -generic ACT1_AW=$act1_aw

source [file join $root fpga/constraints/top_board_timing.tcl]

report_utilization -file $outdir/synth_utilization.rpt
report_utilization -hierarchical -file $outdir/synth_utilization_hier.rpt
report_timing_summary -file $outdir/synth_timing_summary.rpt

opt_design
place_design
phys_opt_design
route_design

report_utilization -file $outdir/impl_utilization.rpt
report_utilization -hierarchical -file $outdir/impl_utilization_hier.rpt
report_timing_summary -check_timing_verbose -file $outdir/impl_timing_summary.rpt
report_clocks -file $outdir/impl_clocks.rpt
report_clock_interaction -file $outdir/impl_clock_interaction.rpt
report_clock_utilization -file $outdir/impl_clock_utilization.rpt
report_io -file $outdir/impl_io.rpt
report_power -file $outdir/impl_power.rpt
report_drc -file $outdir/impl_drc.rpt
report_methodology -file $outdir/impl_methodology.rpt
# Clock-domain crossings (ADR-021): every crossing by class, and the bus skew of the FIFO pointers.
report_cdc -file $outdir/impl_cdc.rpt
report_cdc -details -file $outdir/impl_cdc_details.rpt
report_bus_skew -file $outdir/impl_bus_skew.rpt
report_route_status -file $outdir/impl_route_status.rpt

# Key figures in one small file, so the Python side does not have to parse the big reports.
proc slack_of {clk type} {
    set paths [get_timing_paths -group $clk -delay_type $type -max_paths 1 -quiet]
    if {[llength $paths] == 0} { return "NA" }
    return [get_property SLACK [lindex $paths 0]]
}
set fp [open $outdir/summary.txt w]
puts $fp "label \[VIVADO-STA\]"
puts $fp "vivado [version -short]"
puts $fp "part $part"
puts $fp "top $top"
puts $fp "K $k"
puts $fp "LANE_IMPL $impl"
puts $fp "C3_EN $c3"
puts $fp "SAFE_DIV $safe_div"
foreach clk [get_clocks] {
    set name [get_property NAME $clk]
    puts $fp "clock $name period_ns [get_property PERIOD $clk] wns_ns [slack_of $name max] whs_ns [slack_of $name min]"
}
puts $fp "design_wns_ns [get_property SLACK [lindex [get_timing_paths -delay_type max -max_paths 1] 0]]"
puts $fp "design_whs_ns [get_property SLACK [lindex [get_timing_paths -delay_type min -max_paths 1] 0]]"
puts $fp "lut [llength [get_cells -hierarchical -filter {REF_NAME =~ LUT*}]]"
puts $fp "ff [llength [get_cells -hierarchical -filter {REF_NAME =~ FD*}]]"
puts $fp "ramb36 [llength [get_cells -hierarchical -filter {REF_NAME =~ RAMB36*}]]"
puts $fp "ramb18 [llength [get_cells -hierarchical -filter {REF_NAME =~ RAMB18*}]]"
puts $fp "dsp48 [llength [get_cells -hierarchical -filter {REF_NAME =~ DSP48*}]]"
puts $fp "mmcm [llength [get_cells -hierarchical -filter {REF_NAME =~ MMCME2*}]]"
puts $fp "bufg [llength [get_cells -hierarchical -filter {REF_NAME =~ BUFG*}]]"
puts $fp "unrouted_nets [llength [get_nets -hierarchical -filter {ROUTE_STATUS == UNROUTED} -quiet]]"
close $fp

write_checkpoint -force [file join $root build/official_post_route.dcp]
puts "OFFICIAL done"
