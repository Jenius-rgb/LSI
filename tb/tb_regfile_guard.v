`timescale 1ns / 1ps
`default_nettype none

// M20 (ADR-021, SPEC 7.8): writes to the INJ* registers are ignored while STATUS.BUSY is set,
// because those signals cross into clk_fast without a synchronizer.  Other writes still work.
`include "sentinel_regmap.vh"
module tb_regfile_guard;
    reg clk = 1'b0;
    reg rst = 1'b1;
    reg bus_wr = 1'b0;
    reg [11:0] bus_addr = 12'd0;
    reg [7:0]  bus_wdata = 8'd0;
    reg busy = 1'b0;
    always #4 clk = ~clk;

    wire [1:0] inj_en, inj_any, inj_oneshot;
    wire [7:0] inj_layer;
    wire [31:0] inj_unit;
    wire [11:0] inj_lane;
    wire [95:0] inj_mask;
    wire [7:0] gov_turbo_mask;

    regfile dut (
        .clk(clk), .rst(rst), .bus_wr(bus_wr), .bus_rd(1'b0), .bus_addr(bus_addr), .bus_wdata(bus_wdata), .bus_rdata(),
        .start(), .soft_reset(), .mode(), .c3_on(), .trust_csum(), .img_sel(),
        .gov_init(), .gov_auto(), .gov_level(), .gov_turbo_mask(gov_turbo_mask), .gov_n_up(), .gov_cooldown(), .gov_corr_hi(),
        .gov_l_min(), .gov_l_max(), .clk_reconfig_start(), .clk_reconfig_level(),
        .inj_en(inj_en), .inj_any(inj_any), .inj_oneshot(inj_oneshot), .inj_layer(inj_layer), .inj_unit(inj_unit),
        .inj_lane(inj_lane), .inj_mask(inj_mask),
        .busy(busy), .done_flag(1'b0), .fatal(1'b0), .log_ovf(1'b0), .mmcm2_locked(1'b1), .fast_is_turbo(1'b0),
        .result_class(4'd0), .cycles_total(32'd0), .cycles_recompute(32'd0), .starve_cycles(32'd0),
        .gov_state_level(4'd0), .gov_state_streak(8'd0), .gov_state_turbo(8'd0), .clk_reconfig_busy(1'b0), .clk_locked(1'b1),
        .lane_status(32'd0), .temp(32'd0), .cnt_addr(), .cnt_data(32'd0));

    task wr(input [11:0] addr, input [7:0] data);
        begin
            @(posedge clk); bus_wr <= 1'b1; bus_addr <= addr; bus_wdata <= data;
            @(posedge clk); bus_wr <= 1'b0;
        end
    endtask

    integer checks = 0, passed = 0;
    task check(input cond, input [8*48-1:0] what);
        begin
            checks = checks + 1;
            if (cond) passed = passed + 1; else $display("FAIL %0s", what);
        end
    endtask

    initial begin
        repeat (3) @(posedge clk);
        rst <= 1'b0;
        busy <= 1'b1;
        wr(`SNT_REG_INJ0_CTRL, 8'h01);
        wr(`SNT_REG_INJ0_MASK_LO, 8'hA5);
        wr(`SNT_REG_INJ1_UNIT, 8'h07);
        @(posedge clk);
        check(inj_en == 2'b00, "INJ0_CTRL written while busy");
        check(inj_mask[7:0] == 8'h00, "INJ0_MASK_LO written while busy");
        check(inj_unit[23:16] == 8'h00, "INJ1_UNIT written while busy");
        wr(`SNT_REG_GOV_CTRL + 12'd2, 8'h3C);   // a register outside INJ* still takes writes
        @(posedge clk);
        check(gov_turbo_mask == 8'h3C, "GOV_CTRL ignored while busy");
        busy <= 1'b0;
        wr(`SNT_REG_INJ0_CTRL, 8'h01);
        wr(`SNT_REG_INJ0_MASK_LO, 8'hA5);
        @(posedge clk);
        check(inj_en == 2'b01, "INJ0_CTRL not written while idle");
        check(inj_mask[7:0] == 8'hA5, "INJ0_MASK_LO not written while idle");
        if (passed == checks) $display("PASS %0d/%0d", passed, checks);
        else begin $display("FAIL %0d/%0d", passed, checks); $fatal(1); end
        $finish;
    end
endmodule

`default_nettype wire
