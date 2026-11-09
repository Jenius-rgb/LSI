`timescale 1ns / 1ps

// Plays golden-model operand sets through lane_array, with random bubbles, and compares
// every serialized result word.  Prints PASS n/n, or FAIL with the first mismatch.
module tb_lane_array;
    parameter K         = 8;
    parameter C3_EN     = 0;
    parameter LANE_IMPL = 0;
    parameter WC1_W     = 11;
    parameter WC2_W     = 14;
    parameter WC3_W     = 16;
    parameter MAX_OPS   = 2000000;
    parameter MAX_WORDS = 400000;
    parameter BUBBLE_PCT = 10;

    localparam ACC_CS_W = 48;
    localparam NCS      = 2 + C3_EN;
    localparam WORDS    = K + NCS;
    localparam OP_W     = 1 + 8 + K*8 + WC1_W + WC2_W + WC3_W;

    reg [OP_W-1:0]       ops [0:MAX_OPS-1];
    reg [ACC_CS_W-1:0]   exp [0:MAX_WORDS-1];
    reg [8*200-1:0]      stim_path, exp_path;
    integer              n_ops, n_words;

    reg clk = 0;
    reg rst = 1;
    always #5 clk = ~clk;

    reg                 op_valid = 0;
    reg                 op_last = 0;
    reg [7:0]           op_a = 0;
    reg [K*8-1:0]       op_w = 0;
    reg [WC1_W-1:0]     op_wc1 = 0;
    reg [WC2_W-1:0]     op_wc2 = 0;
    reg [WC3_W-1:0]     op_wc3 = 0;
    wire                res_valid;
    wire [ACC_CS_W-1:0] res_data;

    lane_array #(.K(K), .C3_EN(C3_EN), .WC1_W(WC1_W), .WC2_W(WC2_W), .WC3_W(WC3_W),
                 .LANE_IMPL(LANE_IMPL), .INJ_EN(0)) dut (
        .clk(clk), .rst(rst),
        .op_valid(op_valid), .op_last(op_last), .op_pass_start(1'b0),
        .op_a(op_a), .op_w(op_w), .op_wc1(op_wc1), .op_wc2(op_wc2), .op_wc3(op_wc3),
        .inj_en(2'b00), .inj_any(2'b00), .inj_oneshot(2'b00), .inj_rearm(1'b0),
        .inj_unit({32{1'b0}}), .inj_lane({12{1'b0}}), .inj_mask({96{1'b0}}),
        .res_valid(res_valid), .res_data(res_data));

    integer got = 0;
    integer errors = 0;

    always @(posedge clk) begin
        if (!rst && res_valid) begin
            if (got >= n_words) begin
                if (errors == 0) $display("FAIL extra word beyond %0d expected", n_words);
                errors = errors + 1;
            end else if (res_data !== exp[got]) begin
                if (errors == 0)
                    $display("FAIL word=%0d unit=%0d lane_pos=%0d expected=%h got=%h",
                             got, got / WORDS, got % WORDS, exp[got], res_data);
                errors = errors + 1;
            end
            got = got + 1;
        end
    end

    integer idx = 0;
    integer seed = 12345;
    integer idle = 0;

    initial begin
        if (!$value$plusargs("stim=%s", stim_path) || !$value$plusargs("exp=%s", exp_path) ||
            !$value$plusargs("n_ops=%d", n_ops) || !$value$plusargs("n_words=%d", n_words)) begin
            $display("FAIL missing plusargs");
            $fatal(1);
        end
        $readmemh(stim_path, ops);
        $readmemh(exp_path, exp);
        repeat (5) @(posedge clk);
        @(negedge clk) rst = 0;

        while (idx < n_ops) begin
            @(negedge clk);
            if (($random(seed) & 32'h7fffffff) % 100 < BUBBLE_PCT) begin
                op_valid = 0;
                op_last  = 0;
                op_a     = 8'hxx;
                op_w     = {K*8{1'bx}};
            end else begin
                {op_last, op_a, op_w, op_wc3, op_wc2, op_wc1} = ops[idx];
                op_valid = 1;
                idx = idx + 1;
            end
        end
        @(negedge clk);
        op_valid = 0;
        op_last  = 0;

        while (got < n_words && idle < 2000) begin
            @(negedge clk);
            idle = idle + 1;
        end
        repeat (20) @(negedge clk);

        if (errors != 0 || got != n_words) begin
            $display("FAIL errors=%0d words=%0d/%0d", errors, got, n_words);
            $fatal(1);
        end
        $display("PASS %0d/%0d", got, n_words);
        $finish;
    end
endmodule
