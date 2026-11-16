# Clock relationships of the complete design (SPEC 7.8).  Sourced by fpga/synth_official.tcl
# after synth_design, when the clock primitives exist in the netlist.
#
# clk_fast is the output of the one BUFGCTRL: a glitch-free mux of the safe clock (I0) and the
# turbo clock (I1).  The two clocks on that output can never be present together, and the fast
# domain talks to the safe domain only through the asynchronous FIFOs.

set mux [get_cells -hierarchical -filter {REF_NAME == BUFGCTRL}]
if {[llength $mux] != 1} {
    error "expected exactly one BUFGCTRL (the clk_fast mux), found [llength $mux]"
}
set mux_o  [get_pins -of_objects $mux -filter {REF_PIN_NAME == O}]
set mux_i0 [get_pins -of_objects $mux -filter {REF_PIN_NAME == I0}]
set mux_i1 [get_pins -of_objects $mux -filter {REF_PIN_NAME == I1}]
set safe_clk  [get_clocks -of_objects $mux_i0]
set turbo_clk [get_clocks -of_objects $mux_i1]
if {[llength $safe_clk] != 1 || [llength $turbo_clk] != 1} {
    error "the clk_fast mux inputs must each carry exactly one clock"
}

# The first definition replaces the clocks that propagate through the mux; the second is added to it.
create_generated_clock -name clk_fast_safe  -source $mux_i0 -divide_by 1 $mux_o
create_generated_clock -name clk_fast_turbo -source $mux_i1 -divide_by 1 -master_clock $turbo_clk -add $mux_o
set_clock_groups -physically_exclusive -group clk_fast_safe -group clk_fast_turbo
set_clock_groups -asynchronous -group $safe_clk -group {clk_fast_safe clk_fast_turbo}

# The power-on reset is launched by the board clock and enters the clk_safe domain through its
# own synchronizer in top_core (ADR-021).  The input of a synchronizer has no timing requirement.
set por_meta0 [get_cells -hierarchical -filter {NAME =~ "*por_meta_reg[0]"}]
if {[llength $por_meta0] != 1} {
    error "expected exactly one first stage of the power-on reset synchronizer, found [llength $por_meta0]"
}
set_false_path -from [get_clocks clk_in] -to $por_meta0

puts "TIMING safe_clock [get_property NAME $safe_clk] period [get_property PERIOD $safe_clk]"
puts "TIMING turbo_clock [get_property NAME $turbo_clk] period [get_property PERIOD $turbo_clk]"
