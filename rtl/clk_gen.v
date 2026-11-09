`timescale 1ns / 1ps
`default_nettype none

// Clock generator wrapper (SPEC 7.6): selects the Xilinx or the behavioural implementation.
module clk_gen #(
    parameter LEVELS_LOG2 = 4
) (
    input  wire                   clk_in,
    input  wire                   rst,
    output wire                   clk_safe,
    output wire                   clk_fast,
    output wire                   locked,
    input  wire                   sel_turbo,
    output wire                   is_turbo,
    input  wire                   reconfig_start,
    input  wire [LEVELS_LOG2-1:0] reconfig_level,
    output wire                   reconfig_busy,
    output wire                   turbo_locked
);
`ifdef SENTINEL_XILINX
    clk_gen_xilinx #(.LEVELS_LOG2(LEVELS_LOG2)) u_clk (
        .clk_in(clk_in), .rst(rst), .clk_safe(clk_safe), .clk_fast(clk_fast), .locked(locked),
        .sel_turbo(sel_turbo), .is_turbo(is_turbo), .reconfig_start(reconfig_start),
        .reconfig_level(reconfig_level), .reconfig_busy(reconfig_busy), .turbo_locked(turbo_locked));
`else
    clk_gen_sim #(.LEVELS_LOG2(LEVELS_LOG2)) u_clk (
        .clk_in(clk_in), .rst(rst), .clk_safe(clk_safe), .clk_fast(clk_fast), .locked(locked),
        .sel_turbo(sel_turbo), .is_turbo(is_turbo), .reconfig_start(reconfig_start),
        .reconfig_level(reconfig_level), .reconfig_busy(reconfig_busy), .turbo_locked(turbo_locked));
`endif
endmodule

`default_nettype wire
