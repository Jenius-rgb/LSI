`timescale 1ns / 1ps
`default_nettype none

// Asynchronous FIFO with first-word fall-through.  Selects the Xilinx or the portable
// implementation (SPEC 7.3).  afull asserts when at most AFULL_MARGIN entries are free.
module cdc_fifo #(
    parameter WIDTH        = 16,
    parameter DEPTH_LOG2   = 4,
    parameter AFULL_MARGIN = 4
) (
    input  wire             wr_clk,
    input  wire             wr_rst,
    input  wire             wr_en,
    input  wire [WIDTH-1:0] wr_data,
    output wire             afull,
    input  wire             rd_clk,
    input  wire             rd_rst,
    input  wire             rd_en,
    output wire [WIDTH-1:0] rd_data,
    output wire             empty
);
`ifdef SENTINEL_XILINX
    cdc_fifo_xpm #(.WIDTH(WIDTH), .DEPTH_LOG2(DEPTH_LOG2), .AFULL_MARGIN(AFULL_MARGIN)) u_fifo (
        .wr_clk(wr_clk), .wr_rst(wr_rst), .wr_en(wr_en), .wr_data(wr_data), .afull(afull),
        .rd_clk(rd_clk), .rd_rst(rd_rst), .rd_en(rd_en), .rd_data(rd_data), .empty(empty));
`else
    cdc_fifo_sim #(.WIDTH(WIDTH), .DEPTH_LOG2(DEPTH_LOG2), .AFULL_MARGIN(AFULL_MARGIN)) u_fifo (
        .wr_clk(wr_clk), .wr_rst(wr_rst), .wr_en(wr_en), .wr_data(wr_data), .afull(afull),
        .rd_clk(rd_clk), .rd_rst(rd_rst), .rd_en(rd_en), .rd_data(rd_data), .empty(empty));
`endif
endmodule

`default_nettype wire
