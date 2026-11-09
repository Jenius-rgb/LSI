`timescale 1ns / 1ps
`default_nettype none

// Asynchronous FIFO wrapper around xpm_fifo_async (UG953). Only used under Vivado.
module cdc_fifo_xpm #(
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
    localparam DEPTH = 1 << DEPTH_LOG2;
    // xpm_fifo_async accepts PROG_FULL_THRESH only in [7, DEPTH - 5].
    localparam integer THRESH_RAW = DEPTH - AFULL_MARGIN;
    localparam integer THRESH = (THRESH_RAW > DEPTH - 5) ? DEPTH - 5 : ((THRESH_RAW < 7) ? 7 : THRESH_RAW);

    xpm_fifo_async #(
        .FIFO_MEMORY_TYPE("distributed"),
        .FIFO_WRITE_DEPTH(DEPTH),
        .WRITE_DATA_WIDTH(WIDTH),
        .READ_DATA_WIDTH(WIDTH),
        .READ_MODE("fwft"),
        .FIFO_READ_LATENCY(0),
        .PROG_FULL_THRESH(THRESH),
        .USE_ADV_FEATURES("0002"),
        .CDC_SYNC_STAGES(2)
    ) u_xpm (
        .rst(wr_rst),
        .wr_clk(wr_clk),
        .wr_en(wr_en),
        .din(wr_data),
        .prog_full(afull),
        .rd_clk(rd_clk),
        .rd_en(rd_en),
        .dout(rd_data),
        .empty(empty),
        .sleep(1'b0),
        .injectsbiterr(1'b0),
        .injectdbiterr(1'b0)
    );

    wire unused_rd_rst = &{1'b0, rd_rst};
endmodule

`default_nettype wire
