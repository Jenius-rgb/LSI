`timescale 1ns / 1ps
`default_nettype none

// Checksum weights of one K-byte weight word (SPEC 6.1):
//   wc1 = sum(w_k), wc2 = sum(k*w_k), wc3 = sum(k*k*w_k), k = 1..K.
// ADR-029: every constant product is split into shifted copies of w_k, one per set bit of k (wc2) or
// k*k (wc3), and all copies of one output feed a single flat adder tree whose middle level is
// registered, so the two pipeline stages hold about the same number of adders (Parhi ch. 13 and 15).
// Latency: 2 cycles, as before.  Constant multiplications stay in fabric, not DSP slices.
(* use_dsp = "no" *)
module wc_gen #(
    parameter K     = 8,
    parameter C3_EN = 0,
    parameter W_W   = 8,
    parameter WC1_W = 11,
    parameter WC2_W = 14,
    parameter WC3_W = 16
) (
    input  wire             clk,
    input  wire [K*W_W-1:0] w,
    output wire [WC1_W-1:0] wc1,
    output wire [WC2_W-1:0] wc2,
    output wire [WC3_W-1:0] wc3
);
    function integer popcount;
        input integer value;
        integer v;
        begin
            popcount = 0;
            for (v = value; v > 0; v = v / 2)
                popcount = popcount + (v % 2);
        end
    endfunction

    // Number of shifted copies for lanes 1..k with constant j^p (p = 1: wc2, p = 2: wc3).
    function integer n_terms;
        input integer k;
        input integer p;
        integer j;
        begin
            n_terms = 0;
            for (j = 1; j <= k; j = j + 1)
                n_terms = n_terms + popcount(p == 1 ? j : j * j);
        end
    endfunction

    function integer pow2_ceil;
        input integer value;
        integer v;
        begin
            v = 1;
            while (v < value)
                v = v * 2;
            pow2_ceil = v;
        end
    endfunction

    function integer floor_log2;
        input integer value;
        integer v;
        begin
            floor_log2 = 0;
            for (v = value; v > 1; v = v / 2)
                floor_log2 = floor_log2 + 1;
        end
    endfunction

    localparam integer N2 = pow2_ceil(n_terms(K, 1));  // K = 8: 13 copies -> 16 leaves
    localparam integer N3 = pow2_ceil(n_terms(K, 2));  // K = 8: 14 copies -> 16 leaves
    localparam integer MB = floor_log2(K * K) + 1;     // bits of the largest constant K*K

    // Shifted copies packed densely from leaf 0, unused leaves zero.  One function per output keeps a
    // single driver per leaf vector (many part-select drivers make event simulators slow).
    function [N2*WC2_W-1:0] copies2;
        input [K*W_W-1:0] word;
        integer j, b, t;
        reg [WC2_W-1:0] x;
        begin
            copies2 = {N2*WC2_W{1'b0}};
            t = 0;
            for (j = 1; j <= K; j = j + 1) begin
                x = {{(WC2_W-W_W){word[j*W_W-1]}}, word[(j-1)*W_W +: W_W]};
                for (b = 0; b < MB; b = b + 1)
                    if (((j >> b) & 1) != 0) begin
                        copies2[t*WC2_W +: WC2_W] = x << b;
                        t = t + 1;
                    end
            end
        end
    endfunction

    function [N3*WC3_W-1:0] copies3;
        input [K*W_W-1:0] word;
        integer j, b, t;
        reg [WC3_W-1:0] x;
        begin
            copies3 = {N3*WC3_W{1'b0}};
            t = 0;
            for (j = 1; j <= K; j = j + 1) begin
                x = {{(WC3_W-W_W){word[j*W_W-1]}}, word[(j-1)*W_W +: W_W]};
                for (b = 0; b < MB; b = b + 1)
                    if ((((j * j) >> b) & 1) != 0) begin
                        copies3[t*WC3_W +: WC3_W] = x << b;
                        t = t + 1;
                    end
            end
        end
    endfunction

    wire [K*WC1_W-1:0]  leaf1;
    wire [N2*WC2_W-1:0] leaf2 = copies2(w);
    wire [N3*WC3_W-1:0] leaf3 = copies3(w);

    genvar k;
    generate
        for (k = 0; k < K; k = k + 1) begin : lane
            wire [W_W-1:0] wk = w[k*W_W +: W_W];
            assign leaf1[k*WC1_W +: WC1_W] = {{(WC1_W-W_W){wk[W_W-1]}}, wk};
        end
    endgenerate

    sum_tree #(.N(K), .OUT_W(WC1_W)) u_sum1 (.clk(clk), .in(leaf1), .out(wc1));
    sum_tree #(.N(N2), .OUT_W(WC2_W), .PIPE_LEVEL(floor_log2(N2) / 2)) u_sum2 (.clk(clk), .in(leaf2), .out(wc2));

    generate
        if (C3_EN != 0) begin : with_c3
            sum_tree #(.N(N3), .OUT_W(WC3_W), .PIPE_LEVEL(floor_log2(N3) / 2)) u_sum3 (.clk(clk), .in(leaf3), .out(wc3));
        end else begin : no_c3
            assign wc3 = {WC3_W{1'b0}};
            wire unused_leaf3 = &{1'b0, leaf3};
        end
    endgenerate
endmodule

`default_nettype wire
