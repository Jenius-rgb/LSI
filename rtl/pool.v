`timescale 1ns / 1ps
`default_nettype none

// 2x2 max pooling across the four computing units of a window (SPEC 3.4).
// A per-lane buffer tracks the running maximum; position 3 produces the final value.
module pool #(
    parameter K = 8
) (
    input  wire                 clk,
    input  wire                 valid,
    input  wire [$clog2(K)-1:0] lane,
    input  wire [1:0]           pos,
    input  wire [7:0]           value,
    output wire [7:0]           pooled
);
    reg [7:0] best [0:K-1];

    wire [7:0] held = (pos == 2'd0) ? 8'd0 : best[lane];
    assign pooled = (value > held) ? value : held;

    always @(posedge clk)
        if (valid) best[lane] <= pooled;
endmodule

`default_nettype wire
