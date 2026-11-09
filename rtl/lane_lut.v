`timescale 1ns / 1ps
`default_nettype none

// MAC lane with the multiplier built from LUTs.
//   stage 1: operand registers
//   stage 2: product register
//   stage 3: accumulator
// acc_last pulses for one cycle while acc holds a finished unit.
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
    localparam P_W = W_W + 9;

    reg [7:0]           a_r;
    reg signed [W_W-1:0] w_r;
    reg                 first;
    reg                 v1, l1, f1;
    reg                 v2, l2, f2;

    (* use_dsp = "no" *) reg signed [P_W-1:0] p;

    wire [ACC_W-1:0] base = f2 ? {ACC_W{1'b0}} : acc;
    wire [ACC_W-1:0] p_ext = {{(ACC_W-P_W){p[P_W-1]}}, p};

    always @(posedge clk) begin
        a_r <= a;
        w_r <= w;
        p   <= $signed({1'b0, a_r}) * w_r;
        if (rst) begin
            first    <= 1'b1;
            v1       <= 1'b0;
            l1       <= 1'b0;
            f1       <= 1'b0;
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
            v2 <= v1;
            l2 <= l1;
            f2 <= f1;
            if (v2) acc <= base + p_ext;
            acc_last <= v2 & l2;
        end
    end
endmodule

`default_nettype wire
