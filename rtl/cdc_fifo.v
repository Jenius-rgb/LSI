`timescale 1ns / 1ps
`default_nettype none

// Asynchronous FIFO with first-word fall-through.  Selects the Xilinx or the portable
// implementation (SPEC 7.3).  afull asserts when at most AFULL_MARGIN entries are free.
//
// A wide word can be split over SLICES independent FIFOs, each with its own pointers, to keep
// the fanout of the read pointers low.  All slices are written and read together; the caller
// reads only when no slice is empty, so they cannot drift apart.
module cdc_fifo #(
    parameter WIDTH        = 16,
    parameter DEPTH_LOG2   = 4,
    parameter AFULL_MARGIN = 4,
    parameter SLICES       = 1
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
    localparam integer SLICE_W = WIDTH / SLICES;

    wire [SLICES-1:0] afull_i, empty_i;
    assign afull = |afull_i;
    assign empty = |empty_i;

    genvar s;
    generate
        for (s = 0; s < SLICES; s = s + 1) begin : slice
            localparam integer LOW = s * SLICE_W;
            localparam integer W   = (s == SLICES - 1) ? WIDTH - LOW : SLICE_W;
`ifdef SENTINEL_XILINX
            cdc_fifo_xpm #(.WIDTH(W), .DEPTH_LOG2(DEPTH_LOG2), .AFULL_MARGIN(AFULL_MARGIN)) u_fifo (
`else
            cdc_fifo_sim #(.WIDTH(W), .DEPTH_LOG2(DEPTH_LOG2), .AFULL_MARGIN(AFULL_MARGIN)) u_fifo (
`endif
                .wr_clk(wr_clk), .wr_rst(wr_rst), .wr_en(wr_en), .wr_data(wr_data[LOW +: W]), .afull(afull_i[s]),
                .rd_clk(rd_clk), .rd_rst(rd_rst), .rd_en(rd_en), .rd_data(rd_data[LOW +: W]), .empty(empty_i[s]));
        end
    endgenerate
endmodule

`default_nettype wire
