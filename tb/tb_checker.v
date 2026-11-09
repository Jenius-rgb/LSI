`timescale 1ns / 1ps

// Feeds checker cases exported from the Python model and compares the decision, the lane
// and the corrected data with model/checker.py.
module tb_checker;
    parameter K     = 8;
    parameter C3_EN = 0;
    parameter MAX_CASES = 40000;

    localparam ACC_CS_W = 48;
    localparam ACC_W    = 32;
    localparam NCS      = 2 + C3_EN;
    localparam WORDS    = K + NCS;
    // Input line:    {mode(2), trust, c3_on, S1, S2, S3, YK..Y1} with every value at 48 bits.
    // Expected line: {outcome(4), lane(8), Y1..YK at 32 bits}.
    localparam IN_W  = 4 + 3*ACC_CS_W + K*ACC_CS_W;
    localparam EXP_W = 12 + K*ACC_W;

    reg [IN_W-1:0]  cases [0:MAX_CASES-1];
    reg [EXP_W-1:0] exp   [0:MAX_CASES-1];
    reg [8*200-1:0] in_path, exp_path;
    integer n_cases;

    reg clk = 0;
    reg rst = 1;
    always #5 clk = ~clk;

    reg [1:0]          mode = 0;
    reg                trust = 0;
    reg                c3_on = 0;
    reg                in_valid = 0;
    reg [ACC_CS_W-1:0] in_data = 0;
    wire               in_ready;
    wire               done;
    wire [2:0]         outcome;
    wire [4:0]         lane;
    reg  [4:0]         y_addr = 0;
    wire [ACC_W-1:0]   y_data;
    reg                ack = 0;

    lane_checker #(.K(K), .C3_EN(C3_EN)) dut (
        .clk(clk), .rst(rst), .mode(mode), .trust_csum_lane(trust), .c3_on(c3_on),
        .in_valid(in_valid), .in_data(in_data), .in_ready(in_ready),
        .done(done), .outcome(outcome), .lane(lane), .y_addr(y_addr), .y_data(y_data), .ack(ack));

    integer c, w, k, errors, latency, max_latency;
    reg [IN_W-1:0]     line;
    reg [EXP_W-1:0]    want;
    reg [ACC_CS_W-1:0] words [0:WORDS-1];
    reg [ACC_W-1:0]    got_y, want_y;
    reg [3:0]          want_outcome;
    reg [7:0]          want_lane;

    initial begin
        if (!$value$plusargs("in=%s", in_path) || !$value$plusargs("exp=%s", exp_path) ||
            !$value$plusargs("n=%d", n_cases)) begin
            $display("FAIL missing plusargs");
            $fatal(1);
        end
        $readmemh(in_path, cases);
        $readmemh(exp_path, exp);
        errors = 0;
        max_latency = 0;
        repeat (4) @(negedge clk);
        rst = 0;

        for (c = 0; c < n_cases; c = c + 1) begin
            line = cases[c];
            want = exp[c];
            {mode, trust, c3_on} = line[IN_W-1 -: 4];
            words[0] = line[(K+2)*ACC_CS_W +: ACC_CS_W];
            words[1] = line[(K+1)*ACC_CS_W +: ACC_CS_W];
            if (C3_EN != 0) words[2] = line[K*ACC_CS_W +: ACC_CS_W];
            for (k = 0; k < K; k = k + 1)
                words[NCS + k] = line[(K-1-k)*ACC_CS_W +: ACC_CS_W];

            @(negedge clk);
            for (w = 0; w < WORDS; w = w + 1) begin
                in_valid = 1;
                in_data  = words[w];
                if (!in_ready) begin
                    $display("FAIL case=%0d checker not ready", c);
                    $fatal(1);
                end
                @(negedge clk);
            end
            in_valid = 0;
            in_data  = {ACC_CS_W{1'bx}};

            latency = 0;
            while (!done && latency < K + 20) begin
                @(negedge clk);
                latency = latency + 1;
            end
            if (latency > max_latency) max_latency = latency;
            if (latency >= K + 20) begin
                $display("FAIL case=%0d timeout", c);
                $fatal(1);
            end

            {want_outcome, want_lane} = want[EXP_W-1 -: 12];
            if ({1'b0, outcome} !== want_outcome || {3'b0, lane} !== want_lane) begin
                if (errors == 0)
                    $display("FAIL case=%0d lane=- expected outcome=%0d/%0d got=%0d/%0d",
                             c, want_outcome, want_lane, outcome, lane);
                errors = errors + 1;
            end
            for (k = 0; k < K; k = k + 1) begin
                y_addr = k[4:0];
                #1;
                got_y  = y_data;
                want_y = want[(K-1-k)*ACC_W +: ACC_W];
                if (got_y !== want_y) begin
                    if (errors == 0)
                        $display("FAIL case=%0d lane=%0d expected=%h got=%h", c, k + 1, want_y, got_y);
                    errors = errors + 1;
                end
            end
            @(negedge clk);
            ack = 1;
            @(negedge clk);
            ack = 0;
        end

        if (errors != 0) begin
            $display("FAIL errors=%0d of %0d", errors, n_cases);
            $fatal(1);
        end
        $display("PASS %0d/%0d max_latency=%0d", n_cases, n_cases, max_latency);
        $finish;
    end
endmodule
