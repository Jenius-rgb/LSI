# Bitstream dry run (ADR-024).  Proves that write_bitstream and its DRC pass on the routed official
# design with the inferred LVCMOS33 I/O standards.  The file goes to build/ only, carries
# NOT_FOR_BOARD in its name, and must not be loaded onto ZERO7: the bank voltages are measured first
# (board/BRINGUP.md step 1), then board/build_bitstream.py makes the real bitstream.
# Run after python tools/run.py synth-official:  vivado -mode batch -source fpga/bitstream_dryrun.tcl
set root [file normalize [file join [file dirname [info script]] ..]]
set out [file join $root build bitstream_dryrun]
file mkdir $out
open_checkpoint [file join $root build official_post_route.dcp]
report_drc -ruledecks {default bitstream_checks} -file [file join $out drc_bitstream.rpt]
write_bitstream -force [file join $out top_board_DRYRUN_NOT_FOR_BOARD.bit]
puts "DRYRUN bitstream written to [file join $out top_board_DRYRUN_NOT_FOR_BOARD.bit]"
