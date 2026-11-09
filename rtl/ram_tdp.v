`timescale 1ns / 1ps
`default_nettype none

// Dual-port block RAM with byte-column write on port A and read-only port B.
// Both ports are synchronous on the same clock.  Port A reads the old value on a write.
module ram_tdp #(
    parameter ADDR_W = 12,
    parameter NB_COL = 1,
    parameter COL_W  = 8
) (
    input  wire                    clk,
    input  wire                    en_a,
    input  wire [NB_COL-1:0]       we_a,
    input  wire [ADDR_W-1:0]       addr_a,
    input  wire [NB_COL*COL_W-1:0] din_a,
    output reg  [NB_COL*COL_W-1:0] dout_a,
    input  wire                    en_b,
    input  wire [ADDR_W-1:0]       addr_b,
    output reg  [NB_COL*COL_W-1:0] dout_b
);
    localparam DEPTH = 1 << ADDR_W;
    reg [NB_COL*COL_W-1:0] mem [0:DEPTH-1];

    integer idx;
    initial begin
        for (idx = 0; idx < DEPTH; idx = idx + 1)
            mem[idx] = {NB_COL*COL_W{1'b0}};
    end

    genvar col;
    generate
        for (col = 0; col < NB_COL; col = col + 1) begin : column
            always @(posedge clk)
                if (en_a && we_a[col])
                    mem[addr_a][col*COL_W +: COL_W] <= din_a[col*COL_W +: COL_W];
        end
    endgenerate

    always @(posedge clk)
        if (en_a) dout_a <= mem[addr_a];

    always @(posedge clk)
        if (en_b) dout_b <= mem[addr_b];
endmodule

`default_nettype wire
