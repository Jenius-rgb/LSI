`timescale 1ns / 1ps
`default_nettype none

// Portable asynchronous FIFO: Gray-coded pointers, 2-FF synchronizers, FWFT read port.
module cdc_fifo_sim #(
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

    reg [WIDTH-1:0] mem [0:DEPTH-1];

    reg [DEPTH_LOG2:0] wr_bin, wr_gray, rd_bin, rd_gray;
    reg [DEPTH_LOG2:0] wr_gray_s1, wr_gray_s2, rd_gray_s1, rd_gray_s2;

    function [DEPTH_LOG2:0] gray2bin;
        input [DEPTH_LOG2:0] gray;
        integer i;
        begin
            gray2bin[DEPTH_LOG2] = gray[DEPTH_LOG2];
            for (i = DEPTH_LOG2 - 1; i >= 0; i = i - 1)
                gray2bin[i] = gray2bin[i+1] ^ gray[i];
        end
    endfunction

    // Write side: free space is computed against a synchronized (stale, hence safe) read pointer.
    wire [DEPTH_LOG2:0] rd_bin_sync = gray2bin(rd_gray_s2);
    wire [DEPTH_LOG2:0] used = wr_bin - rd_bin_sync;
    assign afull = (used >= (DEPTH - AFULL_MARGIN));

    wire [DEPTH_LOG2:0] wr_bin_next = wr_bin + 1'b1;

    always @(posedge wr_clk) begin
        rd_gray_s1 <= rd_gray;
        rd_gray_s2 <= rd_gray_s1;
        if (wr_rst) begin
            wr_bin  <= {(DEPTH_LOG2+1){1'b0}};
            wr_gray <= {(DEPTH_LOG2+1){1'b0}};
            rd_gray_s1 <= {(DEPTH_LOG2+1){1'b0}};
            rd_gray_s2 <= {(DEPTH_LOG2+1){1'b0}};
        end else if (wr_en) begin
            mem[wr_bin[DEPTH_LOG2-1:0]] <= wr_data;
            wr_bin  <= wr_bin_next;
            wr_gray <= wr_bin_next ^ (wr_bin_next >> 1);
        end
    end

    // Read side: the head word is visible as soon as the FIFO is non-empty.
    assign empty   = (rd_gray == wr_gray_s2);
    assign rd_data = mem[rd_bin[DEPTH_LOG2-1:0]];

    wire [DEPTH_LOG2:0] rd_bin_next = rd_bin + 1'b1;

    always @(posedge rd_clk) begin
        wr_gray_s1 <= wr_gray;
        wr_gray_s2 <= wr_gray_s1;
        if (rd_rst) begin
            rd_bin  <= {(DEPTH_LOG2+1){1'b0}};
            rd_gray <= {(DEPTH_LOG2+1){1'b0}};
            wr_gray_s1 <= {(DEPTH_LOG2+1){1'b0}};
            wr_gray_s2 <= {(DEPTH_LOG2+1){1'b0}};
        end else if (rd_en) begin
            rd_bin  <= rd_bin_next;
            rd_gray <= rd_bin_next ^ (rd_bin_next >> 1);
        end
    end
endmodule

`default_nettype wire
