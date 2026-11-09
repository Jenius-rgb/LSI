`timescale 1ns / 1ps

// Single-clock engine test (M6): weights, parameters and images are loaded by backdoor,
// logits and class are compared with the golden model.
// Runs images [first, first+count).  Prints PASS n/n, or FAIL with the first mismatch.
module tb_engine;
    parameter K = 8;
    parameter R = 2;
    parameter C3_EN = 0;
    parameter LANE_IMPL = 0;
    parameter WC1_W = 11;
    parameter WC2_W = 14;
    parameter WC3_W = 16;
    parameter WEIGHT_AW = 12;
    parameter ACT0_AW = 13;
    parameter ACT1_AW = 12;
    parameter MAX_IMAGES = 400;
    parameter MODE = 2;

    localparam IMG_BYTES = 3072;

    reg clk = 0;
    reg rst = 1;
    always #5 clk = ~clk;

    reg         start = 0;
    reg  [1:0]  mode = MODE;
    wire        busy, done, fatal, log_ovf, image_done;
    wire [3:0]  result_class;
    wire [31:0] cycles_total, cycles_recompute, starve_cycles, cnt_data;
    wire [7:0]  host_rdata;
    wire        clk_sel;

    engine #(.K(K), .R(R), .C3_EN(C3_EN), .LANE_IMPL(LANE_IMPL), .INJ_EN(0),
             .WC1_W(WC1_W), .WC2_W(WC2_W), .WC3_W(WC3_W),
             .WEIGHT_AW(WEIGHT_AW), .ACT0_AW(ACT0_AW), .ACT1_AW(ACT1_AW)) dut (
        .clk_safe(clk), .clk_fast(clk), .rst(rst),
        .start(start), .mode(mode), .c3_on(C3_EN != 0), .trust_csum(1'b0), .img_sel(1'b0),
        .turbo_mask(8'h00), .clk_sel_turbo(clk_sel), .clk_is_turbo(clk_sel),
        .host_en(1'b0), .host_we(1'b0), .host_addr(24'd0), .host_wdata(8'd0), .host_rdata(host_rdata),
        .inj_en(2'b00), .inj_any(2'b00), .inj_oneshot(2'b00), .inj_layer(8'd0), .inj_unit(32'd0),
        .inj_lane(12'd0), .inj_mask(96'd0),
        .busy(busy), .done(done), .fatal(fatal), .log_ovf(log_ovf), .result_class(result_class),
        .cycles_total(cycles_total), .cycles_recompute(cycles_recompute), .starve_cycles(starve_cycles),
        .image_done(image_done), .gov_fail_mask(), .gov_corr_total(), .cnt_addr(7'd0), .cnt_data(cnt_data));

    reg [8*200-1:0] path;
    reg [7:0]       image_mem [0:MAX_IMAGES*IMG_BYTES-1];
    reg [31:0]      logit_exp [0:MAX_IMAGES*16-1];
    reg [31:0]      class_exp [0:MAX_IMAGES-1];

    integer first, count, n_classes, ideal_cycles, i, c, o, errors, passed;
    integer total_cycles;

    task fail_stop;
        begin
            $display("FAIL errors=%0d images_passed=%0d/%0d", errors, passed, count);
            $fatal(1);
        end
    endtask

    initial begin
        if (!$value$plusargs("first=%d", first)) first = 0;
        if (!$value$plusargs("count=%d", count)) count = 1;
        if (!$value$plusargs("nclasses=%d", n_classes)) n_classes = 10;
        if (!$value$plusargs("ideal=%d", ideal_cycles)) ideal_cycles = 0;
        if (!$value$plusargs("weights=%s", path)) begin $display("FAIL no weights"); $fatal(1); end
        $readmemh(path, dut.u_wram.mem);
        if (!$value$plusargs("params=%s", path)) begin $display("FAIL no params"); $fatal(1); end
        $readmemh(path, dut.u_pram.mem);
        if (!$value$plusargs("images=%s", path)) begin $display("FAIL no images"); $fatal(1); end
        $readmemh(path, image_mem);
        if (!$value$plusargs("logits=%s", path)) begin $display("FAIL no logits"); $fatal(1); end
        $readmemh(path, logit_exp);
        if (!$value$plusargs("classes=%s", path)) begin $display("FAIL no classes"); $fatal(1); end
        $readmemh(path, class_exp);

        errors = 0;
        passed = 0;
        total_cycles = 0;
        repeat (10) @(negedge clk);
        rst = 0;
        repeat (5) @(negedge clk);

        for (i = first; i < first + count; i = i + 1) begin
            for (c = 0; c < IMG_BYTES; c = c + 1)
                dut.u_img0.mem[c] = image_mem[i*IMG_BYTES + c];
            start = 1;
            @(negedge clk);
            start = 0;
            wait (done == 1'b1);
            @(negedge clk);
            total_cycles = total_cycles + cycles_total;

            for (o = 0; o < n_classes; o = o + 1) begin
                if (dut.logits[o] !== logit_exp[i*16 + o]) begin
                    if (errors == 0)
                        $display("FAIL image=%0d layer=fc unit=%0d lane=%0d expected=%h got=%h",
                                 i, o / K, o % K, logit_exp[i*16 + o], dut.logits[o]);
                    errors = errors + 1;
                end
            end
            if ({28'd0, result_class} !== class_exp[i]) begin
                if (errors == 0)
                    $display("FAIL image=%0d class expected=%0d got=%0d", i, class_exp[i], result_class);
                errors = errors + 1;
            end
            if (fatal !== 1'b0) begin
                if (errors == 0) $display("FAIL image=%0d FATAL flag set", i);
                errors = errors + 1;
            end
            if (errors != 0) fail_stop;
            passed = passed + 1;
            repeat (3) @(negedge clk);
        end

        $display("PASS %0d/%0d cycles_mean=%0d ideal=%0d", passed, count, total_cycles / count, ideal_cycles);
        $finish;
    end
endmodule
