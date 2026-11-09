`timescale 1ns / 1ps
`default_nettype none

// Balanced adder tree over N = 2^m two's-complement inputs of OUT_W bits.
// One tree level is registered (PIPE_LEVEL, counted from the root) and the output is
// registered, so the latency is 2 cycles.
module sum_tree #(
    parameter N          = 8,
    parameter OUT_W      = 16,
    parameter PIPE_LEVEL = 1
) (
    input  wire               clk,
    input  wire [N*OUT_W-1:0] in,
    output reg  [OUT_W-1:0]   out
);
    wire [OUT_W-1:0] node [0:2*N-2];

    function integer floor_log2;
        input integer value;
        integer v;
        begin
            floor_log2 = 0;
            v = value;
            while (v > 1) begin
                v = v / 2;
                floor_log2 = floor_log2 + 1;
            end
        end
    endfunction

    genvar n;
    generate
        for (n = 0; n < N; n = n + 1) begin : leaf
            assign node[N-1+n] = in[n*OUT_W +: OUT_W];
        end
        for (n = 0; n < N - 1; n = n + 1) begin : inner
            wire [OUT_W-1:0] sum = node[2*n+1] + node[2*n+2];
            if (floor_log2(n + 1) == PIPE_LEVEL) begin : registered
                reg [OUT_W-1:0] r;
                always @(posedge clk) r <= sum;
                assign node[n] = r;
            end else begin : combinational
                assign node[n] = sum;
            end
        end
    endgenerate

    always @(posedge clk) out <= node[0];
endmodule

`default_nettype wire
