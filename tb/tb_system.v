`timescale 1ns / 1ps

// System test (M8, M9): top_core with two clock domains.  Memories and registers are set
// through hierarchical access; START goes through SPI.  Each scenario sets a mode and
// injection slots, runs one image and compares logits, class, flags and every counter with
// the prediction of model/engine_model.py.
module tb_system;
    parameter K = 8;
    parameter R = 2;
    parameter C3_EN = 0;
    parameter LANE_IMPL = 0;
    parameter ZERO_SKIP = 0;
    parameter WC1_W = 11;
    parameter WC2_W = 14;
    parameter WC3_W = 16;
    parameter WEIGHT_AW = 11;
    parameter ACT0_AW = 12;
    parameter ACT1_AW = 10;
    parameter LOG_AW = 8;
    parameter LAYERS = 4;
    parameter MAX_SCEN = 3000;
    parameter MAX_IMAGES = 400;
    parameter IMG_BYTES = 3072;
    parameter real TURBO_NS = 10.0;
    parameter real TURBO_STEP_NS = 0.0;
    parameter AUTO_GOV = 0;
    parameter N_UP = 1;
    parameter L_MAX = 8;

    localparam SCEN_WORDS = 69;

    reg  rst = 1;
    reg  sclk = 0, cs_n = 1, mosi = 0;
    wire miso;
    wire [3:0] led;

    top_core #(.K(K), .R(R), .C3_EN(C3_EN), .LANE_IMPL(LANE_IMPL), .ZERO_SKIP(ZERO_SKIP), .WC1_W(WC1_W), .WC2_W(WC2_W), .WC3_W(WC3_W),
               .WEIGHT_AW(WEIGHT_AW), .ACT0_AW(ACT0_AW), .ACT1_AW(ACT1_AW), .LOG_AW(LOG_AW)) dut (
        .clk_in(1'b0), .rst(rst), .spi_sclk(sclk), .spi_cs_n(cs_n), .spi_mosi(mosi), .spi_miso(miso), .led(led), .ext_wr(1'b0), .ext_rd(1'b0), .ext_addr(24'd0), .ext_wdata(8'd0));

    defparam dut.u_clk.u_clk.TURBO_BASE = TURBO_NS;
    defparam dut.u_clk.u_clk.TURBO_STEP = TURBO_STEP_NS;

    // SPEC 7.7: reconfiguration only with clk_fast on the safe clock; turbo only when locked.
    integer protocol_errors = 0;
    integer reconfigs = 0;
    reg sel_prev = 1'b0;
    always @(posedge dut.clk_safe) begin
        if (!rst && dut.reconfig_start) begin
            reconfigs = reconfigs + 1;
            if (dut.is_turbo !== 1'b0 || dut.sel_turbo !== 1'b0 || dut.u_engine.busy !== 1'b0) begin
                $display("FAIL protocol: reconfiguration started with is_turbo=%b sel=%b busy=%b", dut.is_turbo, dut.sel_turbo, dut.u_engine.busy);
                protocol_errors = protocol_errors + 1;
            end
        end
        if (!rst && dut.sel_turbo === 1'b1 && (dut.reconfig_busy !== 1'b0 || dut.turbo_locked !== 1'b1)) begin
            $display("FAIL protocol: turbo selected while MMCM2 busy or unlocked");
            protocol_errors = protocol_errors + 1;
        end
        if (!rst && sel_prev !== dut.sel_turbo && dut.u_engine.gen_busy === 1'b1) begin
            $display("FAIL protocol: sel changed while the operand generator was running");
            protocol_errors = protocol_errors + 1;
        end
        sel_prev = dut.sel_turbo;
    end

    reg [31:0] scen [0:MAX_SCEN*SCEN_WORDS-1];
    reg [7:0]  images [0:MAX_IMAGES*IMG_BYTES-1];
    reg [8*200-1:0] path;

    integer n, s, i, c, base, errors, passed;
    integer turbo_mask;
    reg [7:0] rx_byte;

    task xfer;
        input  [7:0] tx;
        output [7:0] got;
        integer b;
        begin
            for (b = 7; b >= 0; b = b - 1) begin
                mosi = tx[b];
                #40;
                sclk = 1;
                got[b] = miso;
                #40;
                sclk = 0;
            end
        end
    endtask

    task spi_write_ctrl;
        input [7:0] value;
        reg [7:0] tmp;
        begin
            cs_n = 0;
            #40;
            xfer(8'h02, tmp); xfer(8'h00, tmp); xfer(8'h00, tmp); xfer(8'h08, tmp);
            xfer(value, tmp);
            #40;
            cs_n = 1;
            #80;
        end
    endtask

    task spi_write_reg;
        input [7:0] addr;
        input [7:0] value;
        reg [7:0] tmp;
        begin
            cs_n = 0;
            #40;
            xfer(8'h02, tmp); xfer(8'h00, tmp); xfer(8'h00, tmp); xfer(addr, tmp);
            xfer(value, tmp);
            #40;
            cs_n = 1;
            #80;
        end
    endtask

    task report_counter;
        input [8*16-1:0] name;
        input integer layer;
        input integer expected;
        input integer got;
        begin
            if (errors == 0)
                $display("FAIL scenario=%0d layer=%0d unit=- lane=%0s expected=%0d got=%0d", s, layer, name, expected, got);
            errors = errors + 1;
        end
    endtask

    task check_counter;
        input [8*16-1:0] name;
        input integer layer;
        input integer index;
        input [31:0] expected;
        begin
            if (dut.u_engine.u_counters.mem[index] !== expected)
                report_counter(name, layer, expected, dut.u_engine.u_counters.mem[index]);
        end
    endtask

    integer layer_idx, k_idx;
    reg [31:0] cfg;

    initial begin
        if (!$value$plusargs("scen=%s", path)) begin $display("FAIL no scen"); $fatal(1); end
        $readmemh(path, scen);
        if (!$value$plusargs("images=%s", path)) begin $display("FAIL no images"); $fatal(1); end
        $readmemh(path, images);
        if (!$value$plusargs("n=%d", n)) begin $display("FAIL no n"); $fatal(1); end
        if (!$value$plusargs("weights=%s", path)) begin $display("FAIL no weights"); $fatal(1); end
        $readmemh(path, dut.u_engine.u_wram.mem);
        if (!$value$plusargs("params=%s", path)) begin $display("FAIL no params"); $fatal(1); end
        $readmemh(path, dut.u_engine.u_pram.mem);

        errors = 0;
        passed = 0;
        #200 rst = 0;
        wait (led[3] === 1'b0 || led[3] === 1'b1);
        #500;

        if (AUTO_GOV != 0) begin
            dut.u_regs.gov_param = N_UP | (L_MAX << 28);
            spi_write_reg(8'h20, 8'h03);   // AUTO + INIT pulse
            #200;
        end

        for (s = 0; s < n; s = s + 1) begin
            base = s * SCEN_WORDS;
            for (c = 0; c < IMG_BYTES; c = c + 1)
                dut.u_engine.u_img0.mem[c] = images[scen[base]*IMG_BYTES + c];

            cfg = scen[base + 1];
            dut.u_regs.ctrl         = (cfg[1:0] << 2) | (cfg[3] << 4) | (cfg[2] << 5);
            if (AUTO_GOV == 0) dut.u_regs.gov_ctrl = 32'h00FF0000;    // all layers on turbo
            dut.u_regs.inj0_ctrl    = scen[base + 2];
            dut.u_regs.inj0_unit    = scen[base + 3];
            dut.u_regs.inj0_mask_lo = scen[base + 4];
            dut.u_regs.inj0_mask_hi = scen[base + 5];
            dut.u_regs.inj1_ctrl    = scen[base + 6];
            dut.u_regs.inj1_unit    = scen[base + 7];
            dut.u_regs.inj1_mask_lo = scen[base + 8];
            dut.u_regs.inj1_mask_hi = scen[base + 9];
            #40;

            spi_write_ctrl((cfg[1:0] << 2) | (cfg[3] << 4) | (cfg[2] << 5) | 8'h01);
            wait (dut.u_engine.done == 1'b1);
            wait (dut.u_engine.done == 1'b0);
            #100;

            if ({28'd0, dut.u_engine.result_class} !== scen[base + 10]) begin
                if (errors == 0) $display("FAIL scenario=%0d class expected=%0d got=%0d", s, scen[base+10], dut.u_engine.result_class);
                errors = errors + 1;
            end
            if (dut.u_engine.fatal !== scen[base + 11][0]) begin
                if (errors == 0) $display("FAIL scenario=%0d FATAL expected=%0d got=%0d", s, scen[base+11][0], dut.u_engine.fatal);
                errors = errors + 1;
            end
            if (dut.u_engine.log_ovf !== scen[base + 11][1]) begin
                if (errors == 0) $display("FAIL scenario=%0d LOG_OVF expected=%0d got=%0d", s, scen[base+11][1], dut.u_engine.log_ovf);
                errors = errors + 1;
            end
            for (i = 0; i < 16; i = i + 1) begin
                if (i < scen[base + 68] && dut.u_engine.logits[i] !== scen[base + 12 + i]) begin
                    if (errors == 0)
                        $display("FAIL scenario=%0d layer=fc unit=%0d lane=%0d expected=%h got=%h", s, i / K, i % K, scen[base+12+i], dut.u_engine.logits[i]);
                    errors = errors + 1;
                end
            end
            for (layer_idx = 0; layer_idx < LAYERS; layer_idx = layer_idx + 1) begin
                check_counter("UNITS",     layer_idx, layer_idx*8 + 0, scen[base + 28 + layer_idx*6 + 0]);
                check_counter("CLEAN",     layer_idx, layer_idx*8 + 1, scen[base + 28 + layer_idx*6 + 1]);
                check_counter("CORRECTED", layer_idx, layer_idx*8 + 2, scen[base + 28 + layer_idx*6 + 2]);
                check_counter("CSUM_LANE", layer_idx, layer_idx*8 + 3, scen[base + 28 + layer_idx*6 + 3]);
                check_counter("RECOMPUTE", layer_idx, layer_idx*8 + 4, scen[base + 28 + layer_idx*6 + 4]);
                check_counter("FATAL",     layer_idx, layer_idx*8 + 5, scen[base + 28 + layer_idx*6 + 5]);
            end
            for (k_idx = 0; k_idx < K; k_idx = k_idx + 1)
                check_counter("LANE_CORR", 0, 64 + k_idx, scen[base + 52 + k_idx]);

            if (errors != 0) begin
                $display("FAIL errors=%0d scenarios_passed=%0d/%0d", errors, passed, n);
                $fatal(1);
            end
            passed = passed + 1;
            $display("IMG %0d done cycles=%0d", s, dut.u_engine.cycles_total);   // clk_safe cycles while busy
            $fflush;
            #100;
        end

        if (protocol_errors != 0) begin
            $display("FAIL protocol_errors=%0d", protocol_errors);
            $fatal(1);
        end
        if (AUTO_GOV != 0 && dut.u_gov.level !== L_MAX[3:0]) begin
            $display("FAIL governor level expected=%0d got=%0d", L_MAX, dut.u_gov.level);
            $fatal(1);
        end
        $display("PASS %0d/%0d reconfigs=%0d", passed, n, reconfigs);
        $finish;
    end
endmodule
