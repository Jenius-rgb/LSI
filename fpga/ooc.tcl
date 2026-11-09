# Out-of-context implementation of the accelerator core (SPEC 14).
# Run through fpga/run_matrix.py:
#   vivado -mode batch -source fpga/ooc.tcl -tclargs <part> <K> <impl> <c3> <weight_aw> <act0_aw> <act1_aw> <t_safe_ns> <t_fast_ns> <outdir>

if { $argc != 10 } {
    puts "usage: ooc.tcl part K lane_impl c3 weight_aw act0_aw act1_aw t_safe_ns t_fast_ns outdir"
    exit 2
}
lassign $argv part k impl c3 weight_aw act0_aw act1_aw t_safe t_fast outdir
file mkdir $outdir

set root [file normalize [file join [file dirname [info script]] ..]]
set sources {
    rtl/lane_lut.v rtl/lane_dsp_min.v rtl/lane_dsp_full.v rtl/lane_array.v rtl/lane_checker.v
    rtl/ram_tdp.v rtl/sum_tree.v rtl/wc_gen.v rtl/operand_gen.v rtl/postproc.v rtl/pool.v
    rtl/counter_bank.v rtl/cdc_fifo.v rtl/platform/xilinx/cdc_fifo_xpm.v rtl/fast_path.v rtl/engine.v
}
set_part $part
set_property XPM_LIBRARIES {XPM_CDC XPM_MEMORY XPM_FIFO} [current_project]
foreach f $sources { read_verilog [file join $root $f] }

set wc [exec python -c "import sys; sys.path.insert(0, r'$root/tools'); from sim import wc_widths; print(*wc_widths($k))"]
lassign $wc wc1 wc2 wc3

synth_design -mode out_of_context -top engine -part $part -verilog_define SENTINEL_XILINX=1 \
    -generic K=$k -generic LANE_IMPL=$impl -generic C3_EN=$c3 \
    -generic WC1_W=$wc1 -generic WC2_W=$wc2 -generic WC3_W=$wc3 \
    -generic WEIGHT_AW=$weight_aw -generic ACT0_AW=$act0_aw -generic ACT1_AW=$act1_aw

create_clock -name clk_safe -period $t_safe [get_ports clk_safe]
create_clock -name clk_fast -period $t_fast [get_ports clk_fast]
set_clock_groups -asynchronous -group [get_clocks clk_safe] -group [get_clocks clk_fast]

opt_design
place_design
route_design

report_utilization -hierarchical -file $outdir/utilization_hier.rpt
report_utilization -file $outdir/utilization.rpt
report_timing_summary -file $outdir/timing_summary.rpt
report_timing -max_paths 20 -nworst 1 -group clk_fast -file $outdir/timing_fast.rpt
report_timing -max_paths 20 -nworst 1 -group clk_safe -file $outdir/timing_safe.rpt
report_power -file $outdir/power.rpt

set fp [open $outdir/summary.txt w]
puts $fp "part $part"
puts $fp "K $k"
puts $fp "LANE_IMPL $impl"
puts $fp "C3_EN $c3"
puts $fp "T_SAFE_NS $t_safe"
puts $fp "T_FAST_NS $t_fast"
foreach clk {clk_safe clk_fast} {
    set paths [get_timing_paths -group $clk -max_paths 1 -setup]
    puts $fp "WNS_$clk [expr {[llength $paths] ? [get_property SLACK [lindex $paths 0]] : "NA"}]"
}
close $fp
