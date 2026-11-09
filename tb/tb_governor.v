`timescale 1ns / 1ps

// Plays per-image events and compares the governor's state after every image with
// model/governor.py.  Each scenario starts with an init pulse and its own parameters.
module tb_governor;
    parameter LAYERS = 4;
    parameter MAX_WORDS = 60000;

    localparam ENTRY = 9;

    reg clk = 0, rst = 1, init = 0;
    always #5 clk = ~clk;

    reg  [7:0] n_up = 0, cooldown = 0;
    reg  [15:0] corr_hi = 0;
    reg  [3:0] l_min = 0, l_max = 0;
    reg  image_done = 0, auto_mode = 1;
    reg  [LAYERS-1:0] fail_mask = 0;
    reg  [15:0] corr_total = 0;
    wire [3:0] level;
    wire [LAYERS-1:0] turbo_en;
    wire [7:0] clean_streak;
    wire busy, level_changed;

    governor #(.LAYERS(LAYERS)) dut (
        .clk(clk), .rst(rst), .init(init), .auto_mode(auto_mode),
        .n_up(n_up), .cooldown(cooldown), .corr_hi(corr_hi), .l_min(l_min), .l_max(l_max),
        .image_done(image_done), .fail_mask(fail_mask), .corr_total(corr_total),
        .level(level), .turbo_en(turbo_en), .clean_streak(clean_streak), .busy(busy),
        .level_changed(level_changed));

    // Stream: scenario header {tag=1, n_up, cooldown, corr_hi, l_min, l_max, auto, n_images} as 8 words,
    // then per image {fail_mask, corr_total, level, turbo_mask, streak, cool0..cool3}.
    reg [31:0] words [0:MAX_WORDS-1];
    reg [8*200-1:0] path;
    integer n_words, pc, errors, checks, n_images, im, l, scenario;

    initial begin
        if (!$value$plusargs("vec=%s", path) || !$value$plusargs("n=%d", n_words)) begin
            $display("FAIL missing plusargs");
            $fatal(1);
        end
        $readmemh(path, words);
        errors = 0;
        checks = 0;
        scenario = 0;
        repeat (4) @(negedge clk);
        rst = 0;
        pc = 0;
        while (pc < n_words) begin
            n_up     = words[pc+1][7:0];
            cooldown = words[pc+2][7:0];
            corr_hi  = words[pc+3][15:0];
            l_min    = words[pc+4][3:0];
            l_max    = words[pc+5][3:0];
            auto_mode = words[pc+6][0];
            n_images = words[pc+7];
            pc = pc + 8;
            @(negedge clk);
            init = 1;
            @(negedge clk);
            init = 0;

            for (im = 0; im < n_images; im = im + 1) begin
                fail_mask  = words[pc];
                corr_total = words[pc+1][15:0];
                @(negedge clk);
                image_done = 1;
                @(negedge clk);
                image_done = 0;
                while (busy) @(negedge clk);
                @(negedge clk);
                checks = checks + 1;
                if (level !== words[pc+2][3:0] || {{(32-LAYERS){1'b0}}, turbo_en} !== words[pc+3] || clean_streak !== words[pc+4][7:0]) begin
                    if (errors == 0)
                        $display("FAIL scenario=%0d image=%0d layer=- level exp=%0d got=%0d mask exp=%h got=%h streak exp=%0d got=%0d",
                                 scenario, im, words[pc+2], level, words[pc+3], turbo_en, words[pc+4], clean_streak);
                    errors = errors + 1;
                end
                for (l = 0; l < LAYERS; l = l + 1) begin
                    if (dut.cool[l] !== words[pc+5+l][7:0]) begin
                        if (errors == 0)
                            $display("FAIL scenario=%0d image=%0d layer=%0d cool exp=%0d got=%0d", scenario, im, l, words[pc+5+l], dut.cool[l]);
                        errors = errors + 1;
                    end
                end
                pc = pc + 9;
            end
            scenario = scenario + 1;
        end
        if (errors != 0) begin
            $display("FAIL errors=%0d of %0d", errors, checks);
            $fatal(1);
        end
        $display("PASS %0d/%0d scenarios=%0d", checks, checks, scenario);
        $finish;
    end
endmodule
