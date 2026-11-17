`timescale 1ns / 1ps
`default_nettype none

// wc_gen against the checksum-weight formula (SPEC 6.1); vectors from model/vectors.py (wc_gen_vectors).
// One weight word per cycle; {wc3, wc2, wc1} must match exactly LATENCY cycles later (ADR-029 condition 1).
module tb_wc_gen;
    parameter K         = 8;
    parameter C3_EN     = 0;
    parameter W_W       = 8;
    parameter WC1_W     = 11;
    parameter WC2_W     = 14;
    parameter WC3_W     = 16;
    parameter LATENCY   = 2;
    parameter MAX_CASES = 65536;

    localparam OUT_W = WC1_W + WC2_W + WC3_W;

    reg clk = 1'b0;
    always #5 clk = ~clk;

    reg  [K*W_W-1:0] w = {K*W_W{1'b0}};
    wire [WC1_W-1:0] wc1;
    wire [WC2_W-1:0] wc2;
    wire [WC3_W-1:0] wc3;

    wc_gen #(.K(K), .C3_EN(C3_EN), .W_W(W_W), .WC1_W(WC1_W), .WC2_W(WC2_W), .WC3_W(WC3_W)) dut (
        .clk(clk), .w(w), .wc1(wc1), .wc2(wc2), .wc3(wc3));

    reg [K*W_W-1:0] cases [0:MAX_CASES-1];
    reg [OUT_W-1:0] exp   [0:MAX_CASES-1];
    reg [1023:0] in_path, exp_path;
    integer n_cases, c, errors;
    reg [OUT_W-1:0] got, want;

    initial begin
        if (!$value$plusargs("in=%s", in_path) || !$value$plusargs("exp=%s", exp_path) ||
            !$value$plusargs("n=%d", n_cases)) begin
            $display("FAIL missing plusargs");
            $fatal(1);
        end
        if (n_cases > MAX_CASES) begin
            $display("FAIL n=%0d exceeds MAX_CASES=%0d", n_cases, MAX_CASES);
            $fatal(1);
        end
        $readmemh(in_path, cases, 0, n_cases - 1);
        $readmemh(exp_path, exp, 0, n_cases - 1);
        errors = 0;
        for (c = 0; c < n_cases + LATENCY; c = c + 1) begin
            @(negedge clk);
            if (c >= LATENCY) begin
                got  = {wc3, wc2, wc1};
                want = exp[c - LATENCY];
                if (got !== want) begin
                    if (errors == 0)
                        $display("FAIL case=%0d word=%h expected wc3/wc2/wc1=%h/%h/%h got=%h/%h/%h", c - LATENCY,
                                 cases[c - LATENCY], want[OUT_W-1 -: WC3_W], want[WC1_W +: WC2_W], want[WC1_W-1:0],
                                 wc3, wc2, wc1);
                    errors = errors + 1;
                end
            end
            if (c < n_cases) w = cases[c];
        end
        if (errors != 0) begin
            $display("FAIL errors=%0d of %0d", errors, n_cases);
            $fatal(1);
        end
        $display("PASS %0d/%0d", n_cases, n_cases);
        $finish;
    end
endmodule

`default_nettype wire
