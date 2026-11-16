`timescale 1ns / 1ps
`default_nettype none

// Behavioural stand-in for the XADC DRP (portable model of rtl/platform/xilinx/xadc_prim_xilinx.v).
// Register 00h returns CODE in its 12 MSBs, four clocks after DEN; other addresses return zero.
module xadc_prim_sim #(
    parameter [11:0] CODE = 12'd2423
) (
    input  wire        dclk,
    input  wire        reset,
    input  wire        den,
    input  wire [6:0]  daddr,
    output reg  [15:0] dout,
    output reg         drdy
);
    reg [2:0] delay;
    reg       busy;
    reg [6:0] addr;

    always @(posedge dclk) begin
        drdy <= 1'b0;
        if (reset) begin
            busy  <= 1'b0;
            delay <= 3'd0;
            addr  <= 7'd0;
            dout  <= 16'd0;
        end else if (den) begin
            busy  <= 1'b1;
            delay <= 3'd3;
            addr  <= daddr;
        end else if (busy) begin
            delay <= delay - 1'b1;
            if (delay == 3'd0) begin
                busy <= 1'b0;
                drdy <= 1'b1;
                dout <= (addr == 7'h00) ? {CODE, 4'h0} : 16'h0000;
            end
        end
    end
endmodule

`default_nettype wire
