# Bitstream of top_jtag: ZERO7 without the Raspberry Pi, PC as host over JTAG (ADR-025, ADR-026).
# Run through fpga/bringup/build.py (python tools/run.py bringup jtag_host --accept-inferred-io).
#   vivado -mode batch -source fpga/bringup/jtag_host/build.tcl -tclargs <outdir> <bitname> <safe_div>
if { $argc != 3 } { puts "usage: build.tcl outdir bitname safe_div"; exit 2 }
lassign $argv outdir bitname safe_div
set k 8
set impl 0
set c3 1
set weight_aw 12
set act0_aw 13
set act1_aw 11
set part xc7s25csga225-1
set top top_jtag
file mkdir $outdir

set root [file normalize [file join [file dirname [info script]] .. .. ..]]
set sources {
    rtl/lane_lut.v rtl/lane_dsp_min.v rtl/lane_dsp_full.v rtl/lane_array.v rtl/lane_checker.v
    rtl/ram_tdp.v rtl/sum_tree.v rtl/wc_gen.v rtl/operand_gen.v rtl/postproc.v rtl/pool.v
    rtl/counter_bank.v rtl/cdc_fifo.v rtl/platform/xilinx/cdc_fifo_xpm.v rtl/fast_path.v rtl/engine.v
    rtl/spi_slave.v rtl/regfile.v rtl/governor.v rtl/clk_seq.v rtl/clk_gen.v rtl/axil_bus_bridge.v rtl/jtag_axi_master.v rtl/platform/xilinx/jtag_axi_master_xilinx.v
    rtl/clkwiz_seq.v rtl/platform/xilinx/clk_gen_xilinx.v rtl/xadc_temp.v rtl/platform/xilinx/xadc_prim_xilinx.v rtl/ws2812_tx.v rtl/status_led.v rtl/top_core.v board/top_jtag.v
}
set_part $part
set_property XPM_LIBRARIES {XPM_CDC XPM_MEMORY XPM_FIFO} [current_project]
foreach f $sources { read_verilog [file join $root $f] }
read_xdc [file join $root fpga/bringup/jtag_host/top_jtag.xdc]

# MMCM2 inside a Clocking Wizard v6.0 with AXI4-Lite dynamic reconfiguration (ADR-023, PG065).
# Level 0 of the turbo table equals clk_safe; the IP is regenerated on every run.
set ipdir [file join $root build ip_jtag_host]
file delete -force $ipdir
file mkdir $ipdir
create_ip -name clk_wiz -vendor xilinx.com -library ip -module_name clk_wiz_turbo -dir $ipdir
set turbo_mhz [format %.3f [expr {1000.0 / $safe_div}]]
set_property -dict [list CONFIG.PRIM_IN_FREQ {20.000} CONFIG.PRIM_SOURCE {No_buffer} CONFIG.USE_DYN_RECONFIG {true} CONFIG.INTERFACE_SELECTION {Enable_AXI} CONFIG.CLKOUT1_REQUESTED_OUT_FREQ $turbo_mhz CONFIG.USE_LOCKED {true}] [get_ips clk_wiz_turbo]
set_property GENERATE_SYNTH_CHECKPOINT false [get_files clk_wiz_turbo.xci]
generate_target {synthesis} [get_ips clk_wiz_turbo]
# JTAG-to-AXI Master, AXI4-Lite, 32-bit (ADR-025).
create_ip -name jtag_axi -vendor xilinx.com -library ip -module_name jtag_axi_host -dir $ipdir
set_property -dict [list CONFIG.PROTOCOL {2}] [get_ips jtag_axi_host]
set_property GENERATE_SYNTH_CHECKPOINT false [get_files jtag_axi_host.xci]
generate_target {synthesis} [get_ips jtag_axi_host]
puts "TIMING turbo_ip M [get_property CONFIG.MMCM_CLKFBOUT_MULT_F [get_ips clk_wiz_turbo]] D [get_property CONFIG.MMCM_DIVCLK_DIVIDE [get_ips clk_wiz_turbo]] O [get_property CONFIG.MMCM_CLKOUT0_DIVIDE_F [get_ips clk_wiz_turbo]]"

set wc [exec python -c "import sys; sys.path.insert(0, r'$root/tools'); from sim import wc_widths; print(*wc_widths($k))"]
lassign $wc wc1 wc2 wc3
if {$k != 8 && ($wc1 != 11 || $wc2 != 14 || $wc3 != 16)} {
    puts "ERROR: top_board keeps the checksum weight widths of K = 8; K = $k needs $wc1/$wc2/$wc3"
    exit 2
}

synth_design -top top_jtag -part $part -include_dirs [list [file join $root rtl/gen]] \
    -verilog_define SENTINEL_XILINX=1 -verilog_define SENTINEL_SAFE_DIV=$safe_div \
    -generic K=$k -generic LANE_IMPL=$impl -generic C3_EN=$c3 \
    -generic WEIGHT_AW=$weight_aw -generic ACT0_AW=$act0_aw -generic ACT1_AW=$act1_aw

source [file join $root fpga/constraints/top_board_timing.tcl]
opt_design
place_design
phys_opt_design
route_design
report_utilization -file [file join $outdir utilization.rpt]
report_timing_summary -file [file join $outdir timing_summary.rpt]
report_drc -file [file join $outdir drc.rpt]
write_bitstream -force [file join $outdir $bitname]
write_debug_probes -force [file join $outdir top_jtag.ltx]
puts "BRINGUP bitstream [file join $outdir $bitname]"
