`timescale 1ns / 1ps
`default_nettype none

// Checksum weights of one K-byte weight word (SPEC 6.1):
//   wc1 = sum(w_k), wc2 = sum(k*w_k), wc3 = sum(k*k*w_k), k = 1..K.
// Latency: 2 cycles.  Constant multiplications stay in fabric, not DSP slices.
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
    wire [K*WC1_W-1:0] leaf1;
    wire [K*WC2_W-1:0] leaf2;
    wire [K*WC3_W-1:0] leaf3;

    genvar k;
    generate
        for (k = 0; k < K; k = k + 1) begin : lane
            localparam integer LANE = k + 1;
            localparam integer SQ   = LANE * LANE;
            wire signed [W_W-1:0]   wk = w[k*W_W +: W_W];
            wire signed [WC2_W-1:0] wk2 = {{(WC2_W-W_W){wk[W_W-1]}}, wk};
            wire signed [WC3_W-1:0] wk3 = {{(WC3_W-W_W){wk[W_W-1]}}, wk};
            wire signed [WC2_W-1:0] lane2 = LANE[WC2_W-1:0];
            wire signed [WC3_W-1:0] lane3 = SQ[WC3_W-1:0];
            wire signed [WC2_W-1:0] prod2 = wk2 * lane2;
            wire signed [WC3_W-1:0] prod3 = wk3 * lane3;
            assign leaf1[k*WC1_W +: WC1_W] = {{(WC1_W-W_W){wk[W_W-1]}}, wk};
            assign leaf2[k*WC2_W +: WC2_W] = prod2;
            assign leaf3[k*WC3_W +: WC3_W] = prod3;
        end
    endgenerate

    sum_tree #(.N(K), .OUT_W(WC1_W)) u_sum1 (.clk(clk), .in(leaf1), .out(wc1));
    sum_tree #(.N(K), .OUT_W(WC2_W)) u_sum2 (.clk(clk), .in(leaf2), .out(wc2));

    generate
        if (C3_EN != 0) begin : with_c3
            sum_tree #(.N(K), .OUT_W(WC3_W)) u_sum3 (.clk(clk), .in(leaf3), .out(wc3));
        end else begin : no_c3
            assign wc3 = {WC3_W{1'b0}};
            wire unused_leaf3 = &{1'b0, leaf3};
        end
    endgenerate
endmodule

`default_nettype wire
