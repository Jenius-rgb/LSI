`timescale 1ns / 1ps
`default_nettype none

`include "sentinel_regmap.vh"

// Top level of the accelerator without board pins: SPI host interface, registers,
// engine, governor and clock generator.
module top_core #(
    parameter K          = 8,
    parameter R          = 2,
    parameter C3_EN      = 0,
    parameter LANE_IMPL  = 0,
    parameter INJ_EN     = 1,
    parameter WC1_W      = 11,
    parameter WC2_W      = 14,
    parameter WC3_W      = 16,
    parameter WEIGHT_AW  = 12,
    parameter ACT0_AW    = 13,
    parameter ACT1_AW    = 12,
    parameter LOG_AW     = 8,
    parameter LED_CLK_HZ = 125_000_000   // clk_safe frequency, for the WS2812B pulse timing
) (
    input  wire clk_in,
    input  wire rst,
    input  wire spi_sclk,
    input  wire spi_cs_n,
    input  wire spi_mosi,
    output wire spi_miso,
    output wire [3:0] led,
    output wire       ws2812     // status colour for the WS2812B LED1 (ADR-017)
);
    wire clk_safe, clk_fast, clocks_locked, sel_turbo, is_turbo;
    wire reconfig_start, reconfig_busy, turbo_locked;
    wire [3:0] reconfig_level;
    wire host_reconfig_start;
    wire [3:0] host_reconfig_level;

    clk_gen u_clk (
        .clk_in(clk_in), .rst(rst), .clk_safe(clk_safe), .clk_fast(clk_fast), .locked(clocks_locked),
        .sel_turbo(sel_turbo), .is_turbo(is_turbo),
        .reconfig_start(reconfig_start), .reconfig_level(reconfig_level),
        .reconfig_busy(reconfig_busy), .turbo_locked(turbo_locked));

    // Synchronous reset held until the clocks are stable; soft reset comes from the registers.
    // rst is launched by the board clock and LOCKED is asynchronous.  Each has its own two-flop
    // synchronizer with no logic in front of it (ADR-021); they meet the soft reset in the
    // clk_safe domain.  Every source reaches rst_safe after four flops.  rst_safe_r drives the
    // reset net and may be replicated.
    wire   soft_reset;
    (* ASYNC_REG = "TRUE" *) reg [1:0] por_meta;
    (* ASYNC_REG = "TRUE" *) reg [1:0] lock_meta;
    reg [1:0] soft_d;
    reg       rst_req, rst_safe_r;
    initial begin
        por_meta   = 2'b11;
        lock_meta  = 2'b00;
        soft_d     = 2'b00;
        rst_req    = 1'b1;
        rst_safe_r = 1'b1;
    end
    always @(posedge clk_safe) begin
        por_meta   <= {por_meta[0], rst};
        lock_meta  <= {lock_meta[0], clocks_locked};
        soft_d     <= {soft_d[0], soft_reset};
        rst_req    <= por_meta[1] | ~lock_meta[1] | soft_d[1];
        rst_safe_r <= rst_req;
    end
    wire rst_safe = rst_safe_r;

    // On-chip temperature for the TEMP register (ADR-018, ADR-023).
    wire [11:0] temp_code;
    wire        temp_valid;
    xadc_temp u_temp (.clk(clk_safe), .rst(rst_safe), .code(temp_code), .valid(temp_valid));

    // ---- host bus ------------------------------------------------------------------------
    wire        bus_wr, bus_rd;
    wire [23:0] bus_addr;
    wire [7:0]  bus_wdata;
    wire [7:0]  reg_rdata, eng_rdata;

    wire is_reg = (bus_addr[23:12] == 12'd0);

    reg [2:0] rd_pipe;
    reg       rd_is_reg;
    always @(posedge clk_safe) begin
        rd_pipe <= rst_safe ? 3'd0 : {rd_pipe[1:0], bus_rd};
        if (bus_rd) rd_is_reg <= is_reg;
    end
    wire       bus_rvalid = rd_pipe[2];
    wire [7:0] bus_rdata  = rd_is_reg ? reg_rdata : eng_rdata;

    localparam [7:0] VER_MAJOR = `SNT_VER_MAJOR;
    localparam [7:0] VER_MINOR = `SNT_VER_MINOR;
    localparam [7:0] K_BYTE    = K;
    localparam [1:0] IMPL_BITS = LANE_IMPL;
    localparam [0:0] INJ_BIT   = (INJ_EN != 0);
    localparam [0:0] C3_BIT    = (C3_EN != 0);
    wire [63:0] id_word = {32'h534E544C, VER_MAJOR, VER_MINOR, K_BYTE, 4'd0, IMPL_BITS, INJ_BIT, C3_BIT};

    spi_slave u_spi (
        .clk(clk_safe), .rst(rst_safe), .sclk(spi_sclk), .cs_n(spi_cs_n), .mosi(spi_mosi), .miso(spi_miso),
        .id_word(id_word), .bus_wr(bus_wr), .bus_rd(bus_rd), .bus_addr(bus_addr), .bus_wdata(bus_wdata),
        .bus_rdata(bus_rdata), .bus_rvalid(bus_rvalid));

    // ---- registers -----------------------------------------------------------------------
    wire        start_reg, c3_on, trust_csum, img_sel;
    wire [1:0]  mode;
    wire        gov_auto;
    wire [3:0]  gov_level, gov_l_min, gov_l_max;
    wire [7:0]  gov_turbo_mask, gov_n_up, gov_cooldown, gov_corr_hi;
    wire [1:0]  inj_en, inj_any, inj_oneshot;
    wire [7:0]  inj_layer;
    wire [31:0] inj_unit;
    wire [11:0] inj_lane;
    wire [95:0] inj_mask;
    wire        busy, done, fatal, log_ovf, image_done;
    wire [7:0]  gov_fail_mask;
    wire [15:0] gov_corr_total;
    wire [15:0] lane_status;
    wire        gov_init, gov_busy, gov_level_changed;
    wire        seq_busy;
    reg         start_pending;
    wire        start_engine;
    wire [3:0]  result_class;
    wire [31:0] cycles_total, cycles_recompute, starve_cycles, cnt_data;
    wire [6:0]  cnt_addr;
    wire [3:0]  gov_state_level;
    wire [7:0]  gov_state_streak, gov_state_turbo;
    wire [7:0]  turbo_mask;

    reg  done_flag;
    always @(posedge clk_safe) begin
        if (rst_safe | start_reg) done_flag <= 1'b0;
        else if (done) done_flag <= 1'b1;
    end

    regfile u_regs (
        .clk(clk_safe), .rst(rst_safe),
        .bus_wr(bus_wr & is_reg), .bus_rd(bus_rd & is_reg), .bus_addr(bus_addr[11:0]),
        .bus_wdata(bus_wdata), .bus_rdata(reg_rdata),
        .start(start_reg), .soft_reset(soft_reset), .mode(mode), .c3_on(c3_on),
        .trust_csum(trust_csum), .img_sel(img_sel),
        .gov_auto(gov_auto), .gov_level(gov_level), .gov_turbo_mask(gov_turbo_mask),
        .gov_n_up(gov_n_up), .gov_cooldown(gov_cooldown), .gov_corr_hi(gov_corr_hi),
        .gov_l_min(gov_l_min), .gov_l_max(gov_l_max),
        .gov_init(gov_init),
        .clk_reconfig_start(host_reconfig_start), .clk_reconfig_level(host_reconfig_level),
        .inj_en(inj_en), .inj_any(inj_any), .inj_oneshot(inj_oneshot), .inj_layer(inj_layer),
        .inj_unit(inj_unit), .inj_lane(inj_lane), .inj_mask(inj_mask),
        .busy(busy), .done_flag(done_flag), .fatal(fatal), .log_ovf(log_ovf),
        .mmcm2_locked(turbo_locked), .fast_is_turbo(is_turbo),
        .result_class(result_class), .cycles_total(cycles_total), .cycles_recompute(cycles_recompute),
        .starve_cycles(starve_cycles),
        .gov_state_level(gov_state_level), .gov_state_streak(gov_state_streak), .gov_state_turbo(gov_state_turbo),
        .clk_reconfig_busy(reconfig_busy), .clk_locked(clocks_locked & turbo_locked),
        .lane_status({16'd0, lane_status}), .temp({15'd0, temp_valid, 4'd0, temp_code}),
        .cnt_addr(cnt_addr), .cnt_data(cnt_data));

    // ---- engine ----------------------------------------------------------------------------
    engine #(
        .K(K), .R(R), .C3_EN(C3_EN), .LANE_IMPL(LANE_IMPL), .INJ_EN(INJ_EN),
        .WC1_W(WC1_W), .WC2_W(WC2_W), .WC3_W(WC3_W),
        .WEIGHT_AW(WEIGHT_AW), .ACT0_AW(ACT0_AW), .ACT1_AW(ACT1_AW), .LOG_AW(LOG_AW)
    ) u_engine (
        .clk_safe(clk_safe), .clk_fast(clk_fast), .rst(rst_safe),
        .start(start_engine), .mode(mode), .c3_on(c3_on), .trust_csum(trust_csum), .img_sel(img_sel),
        .turbo_mask(turbo_mask),
        .clk_sel_turbo(sel_turbo), .clk_is_turbo(is_turbo),
        .host_en((bus_wr | bus_rd) & ~is_reg), .host_we(bus_wr), .host_addr(bus_addr),
        .host_wdata(bus_wdata), .host_rdata(eng_rdata),
        .inj_en(INJ_EN != 0 ? inj_en : 2'b00), .inj_any(inj_any), .inj_oneshot(inj_oneshot),
        .inj_layer(inj_layer), .inj_unit(inj_unit), .inj_lane(inj_lane), .inj_mask(inj_mask),
        .busy(busy), .done(done), .fatal(fatal), .log_ovf(log_ovf), .result_class(result_class),
        .cycles_total(cycles_total), .cycles_recompute(cycles_recompute), .starve_cycles(starve_cycles),
        .image_done(image_done), .gov_fail_mask(gov_fail_mask), .gov_corr_total(gov_corr_total),
        .lane_status(lane_status),
        .cnt_addr(cnt_addr), .cnt_data(cnt_data));

    // ---- governor and clock reconfiguration ------------------------------------------------
    wire [3:0] auto_level;
    wire [7:0] auto_turbo;

    governor #(.LAYERS(8)) u_gov (
        .clk(clk_safe), .rst(rst_safe), .init(gov_init), .auto_mode(gov_auto),
        .n_up(gov_n_up), .cooldown(gov_cooldown), .corr_hi({8'd0, gov_corr_hi}),
        .l_min(gov_l_min), .l_max(gov_l_max),
        .image_done(image_done), .fail_mask(gov_fail_mask), .corr_total(gov_corr_total),
        .level(auto_level), .turbo_en(auto_turbo), .clean_streak(gov_state_streak),
        .busy(gov_busy), .level_changed(gov_level_changed));

    assign turbo_mask      = gov_auto ? auto_turbo : gov_turbo_mask;
    assign gov_state_level = auto_level;
    assign gov_state_turbo = auto_turbo;

    // SPEC 7.7: reconfiguration only between images, after clk_fast is back on the safe clock.
    wire seq_request = gov_auto ? gov_level_changed : host_reconfig_start;
    wire [3:0] seq_level = gov_auto ? auto_level : host_reconfig_level;

    clk_seq u_seq (
        .clk(clk_safe), .rst(rst_safe), .request(seq_request), .level(seq_level),
        .is_turbo(is_turbo), .reconfig_busy(reconfig_busy), .turbo_locked(turbo_locked),
        .busy(seq_busy), .reconfig_start(reconfig_start), .reconfig_level(reconfig_level));

    // START waits while the governor or the clock sequencer is working.
    assign start_engine = start_pending & ~busy & ~gov_busy & ~gov_level_changed & ~seq_busy;
    always @(posedge clk_safe) begin
        if (rst_safe | start_engine) start_pending <= 1'b0;
        else if (start_reg) start_pending <= 1'b1;
    end

    assign led = {fatal, is_turbo, done_flag, busy};

    status_led #(.CLK_HZ(LED_CLK_HZ)) u_status_led (
        .clk(clk_safe), .rst(rst_safe), .fatal(fatal), .is_turbo(is_turbo), .done(done_flag), .busy(busy), .dout(ws2812));

    wire unused_top = &{1'b0, gov_level};
endmodule

`default_nettype wire
