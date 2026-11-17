# Build one bring-up design without the Raspberry Pi (ADR-026).  Run through fpga/bringup/build.py.
#   vivado -mode batch -source fpga/bringup/build.tcl -tclargs <top> <rtl files> <xdc> <outdir> <bitname> <ila 0|1>
if { $argc != 6 } { puts "usage: build.tcl top rtl_files xdc outdir bitname ila"; exit 2 }
lassign $argv top rtl_files xdc outdir bitname ila
set part xc7s25csga225-1
file mkdir $outdir
set_part $part
foreach f [split $rtl_files "+"] { read_verilog $f }
read_xdc $xdc
synth_design -top $top -part $part
if { $ila } {
    # ILA on the synchronised inputs and the WS2812B line of io_test_top, clocked by CLK20M.
    set nets [concat [get_nets -quiet {in_sync[*]}] [get_nets -quiet ws2812_dout_OBUF]]
    if { [llength $nets] > 0 } {
        create_debug_core u_ila ila
        set_property C_DATA_DEPTH 4096 [get_debug_cores u_ila]
        connect_debug_port u_ila/clk [get_nets -of_objects [get_pins -hierarchical -filter {NAME =~ *in_sync_reg[0]/C}]]
        set_property port_width [llength $nets] [get_debug_ports u_ila/probe0]
        connect_debug_port u_ila/probe0 $nets
        write_debug_probes -force [file join $outdir $top.ltx]
    }
}
opt_design
place_design
route_design
report_utilization -file [file join $outdir utilization.rpt]
report_timing_summary -file [file join $outdir timing_summary.rpt]
report_drc -file [file join $outdir drc.rpt]
write_bitstream -force [file join $outdir $bitname]
if { $ila } { write_debug_probes -force [file join $outdir $top.ltx] }
puts "BRINGUP bitstream [file join $outdir $bitname]"
