`timescale 1ns / 1ps
`default_nettype none

// Behavioural clock generator (SPEC 7.6): a safe clock, a turbo clock whose period follows
// the requested level, and a glitch-free output mux.
//
// The mux models BUFGCTRL behaviour: the output parks low on the old clock, then starts on
// a rising edge of the new clock.  is_turbo reports the selection actually in force.
// verilator lint_off BLKSEQ
// verilator lint_off PROCASSINIT
// verilator lint_off ZERODLY
// verilator lint_off MULTIDRIVEN
// verilator lint_off STMTDLY
// verilator lint_off UNUSEDSIGNAL
// verilator lint_off UNOPTFLAT
module clk_gen_sim #(
    parameter        LEVELS_LOG2  = 4,
    parameter real   SAFE_PERIOD  = 10.0,
    parameter real   TURBO_BASE   = 10.0,   // turbo period at level 0
    parameter real   TURBO_STEP   = 0.0,    // period reduction per level
    parameter integer RECONFIG_NS = 500
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
    reg  safe = 1'b0;
    reg  turbo = 1'b0;
    real turbo_period = TURBO_BASE;

    always #(SAFE_PERIOD / 2.0) safe = ~safe;
    always #(turbo_period / 2.0) turbo = ~turbo;

    assign clk_safe = safe;
    assign locked   = ~rst;

    // Glitch-free 2:1 mux: the output only follows the currently selected source.
    reg current_turbo = 1'b0;
    reg out = 1'b0;

    always @(negedge safe)  if (!current_turbo && sel_turbo)  current_turbo <= 1'b1;
    always @(negedge turbo) if ( current_turbo && !sel_turbo) current_turbo <= 1'b0;

    always @(safe or turbo or current_turbo) begin
        if (current_turbo) out = turbo;
        else               out = safe;
    end

    assign clk_fast = out;
    assign is_turbo = current_turbo;

    // Reconfiguration: MMCM2 unlocks for a while, then runs at the new period.
    reg busy = 1'b0;
    assign reconfig_busy = busy;
    assign turbo_locked  = ~busy & ~rst;

    always @(posedge safe) begin
        if (reconfig_start && !busy) begin
            busy <= 1'b1;
            #(RECONFIG_NS);
            turbo_period = TURBO_BASE - TURBO_STEP * reconfig_level;
            busy <= 1'b0;
        end
    end

    wire unused_clk_in = clk_in;
endmodule
// verilator lint_on BLKSEQ
// verilator lint_on PROCASSINIT
// verilator lint_on ZERODLY
// verilator lint_on MULTIDRIVEN
// verilator lint_on STMTDLY
// verilator lint_on UNUSEDSIGNAL
// verilator lint_on UNOPTFLAT

`default_nettype wire
