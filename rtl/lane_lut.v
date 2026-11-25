`timescale 1ns / 1ps
`default_nettype none

// MAC lane with the multiplier built from LUTs.
//   stage 1:  operand registers
//   stage 2a: partial products of the two activation nibbles (ADR-031 (b))
//   stage 2b: product register, p = (p_hi << 4) + p_lo
//   stage 3:  accumulator
// acc_last pulses for one cycle while acc holds a finished unit.
//
// ADR-031 (b): the register between the nibble products and their sum cuts the 8 x W_W multiplier, which started the
// worst clk_fast path (9 logic levels), on a feed-forward cutset; every lane and the v/l/f flags get the same extra
// stage, so the sums are unchanged and the lane latency grows by one cycle.
module lane_lut #(
    parameter W_W   = 8,
    parameter ACC_W = 32
) (
    input  wire                  clk,
    input  wire                  rst,
    input  wire                  valid,
    input  wire                  last,
    input  wire [7:0]            a,
    input  wire signed [W_W-1:0] w,
    output reg  [ACC_W-1:0]      acc,
    output reg                   acc_last
);
    localparam P_W = W_W + 9;       // unsigned 8-bit activation times signed W_W-bit weight
    localparam H_W = W_W + 5;       // unsigned 4-bit nibble times signed W_W-bit weight

    // D5 (ADR-031 (c)): one activation register per lane. Every lane registers the same broadcast activation, so
    // synthesis merged these registers into one that drove all K + NCS multipliers; that shared register started the
    // worst clk_fast path (9 levels, 57 % routing, official report of 18 Nov 2026) [VIVADO-STA].
    (* dont_touch = "true" *) reg [7:0] a_r;
    reg signed [W_W-1:0] w_r;
    reg                 first;
    reg                 v1, l1, f1;
    reg                 vm, lm, fm;
    reg                 v2, l2, f2;

    (* use_dsp = "no" *) reg signed [H_W-1:0] p_lo, p_hi;
    (* use_dsp = "no" *) reg signed [P_W-1:0] p;

    wire signed [P_W-1:0] hi_ext = {p_hi, 4'b0000};
    wire signed [P_W-1:0] lo_ext = {{4{p_lo[H_W-1]}}, p_lo};

    wire [ACC_W-1:0] base = f2 ? {ACC_W{1'b0}} : acc;
    wire [ACC_W-1:0] p_ext = {{(ACC_W-P_W){p[P_W-1]}}, p};

    always @(posedge clk) begin
        a_r  <= a;
        w_r  <= w;
        p_lo <= $signed({1'b0, a_r[3:0]}) * w_r;
        p_hi <= $signed({1'b0, a_r[7:4]}) * w_r;
        p    <= hi_ext + lo_ext;
        if (rst) begin
            first    <= 1'b1;
            v1       <= 1'b0;
            l1       <= 1'b0;
            f1       <= 1'b0;
            vm       <= 1'b0;
            lm       <= 1'b0;
            fm       <= 1'b0;
            v2       <= 1'b0;
            l2       <= 1'b0;
            f2       <= 1'b0;
            acc      <= {ACC_W{1'b0}};
            acc_last <= 1'b0;
        end else begin
            v1 <= valid;
            l1 <= valid & last;
            f1 <= first;
            if (valid) first <= last;
            vm <= v1;
            lm <= l1;
            fm <= f1;
            v2 <= vm;
            l2 <= lm;
            f2 <= fm;
            if (v2) acc <= base + p_ext;
            acc_last <= v2 & l2;
        end
    end
endmodule

`default_nettype wire
