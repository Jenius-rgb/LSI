`timescale 1ns / 1ps
`default_nettype none

`include "sentinel_regmap.vh"

// Register file on the byte-wide host bus (SPEC 12.4).  Registers are little-endian 32-bit
// words.  A read of byte 0 of a word latches the whole word, so multi-byte reads are atomic.
module regfile (
    input  wire         clk,
    input  wire         rst,

    input  wire         bus_wr,
    input  wire         bus_rd,
    input  wire [11:0]  bus_addr,
    input  wire [7:0]   bus_wdata,
    output reg  [7:0]   bus_rdata,

    output reg          start,
    output reg          soft_reset,
    output wire [1:0]   mode,
    output wire         c3_on,
    output wire         trust_csum,
    output wire         img_sel,

    output reg          gov_init,
    output wire         gov_auto,
    output wire [3:0]   gov_level,
    output wire [7:0]   gov_turbo_mask,
    output wire [7:0]   gov_n_up,
    output wire [7:0]   gov_cooldown,
    output wire [7:0]   gov_corr_hi,
    output wire [3:0]   gov_l_min,
    output wire [3:0]   gov_l_max,

    output reg          clk_reconfig_start,
    output wire [3:0]   clk_reconfig_level,

    output wire [1:0]   inj_en,
    output wire [1:0]   inj_any,
    output wire [1:0]   inj_oneshot,
    output wire [7:0]   inj_layer,
    output wire [31:0]  inj_unit,
    output wire [11:0]  inj_lane,
    output wire [95:0]  inj_mask,

    input  wire         busy,
    input  wire         done_flag,
    input  wire         fatal,
    input  wire         log_ovf,
    input  wire         mmcm2_locked,
    input  wire         fast_is_turbo,
    input  wire [3:0]   result_class,
    input  wire [31:0]  cycles_total,
    input  wire [31:0]  cycles_recompute,
    input  wire [31:0]  starve_cycles,
    input  wire [3:0]   gov_state_level,
    input  wire [7:0]   gov_state_streak,
    input  wire [7:0]   gov_state_turbo,
    input  wire         clk_reconfig_busy,
    input  wire         clk_locked,
    input  wire [31:0]  lane_status,
    input  wire [31:0]  temp,

    output wire [6:0]   cnt_addr,
    input  wire [31:0]  cnt_data
);
    reg [31:0] ctrl, gov_ctrl, gov_param, clk_ctrl;
    reg [31:0] inj0_ctrl, inj0_unit, inj0_mask_lo, inj0_mask_hi;
    reg [31:0] inj1_ctrl, inj1_unit, inj1_mask_lo, inj1_mask_hi;

    wire [11:0] word_addr = {bus_addr[11:2], 2'b00};
    wire [1:0]  byte_idx  = bus_addr[1:0];
    wire        is_counter = bus_addr[11];

    assign cnt_addr = bus_addr[8:2];

    assign mode       = ctrl[`SNT_CTRL_MODE_LSB + `SNT_CTRL_MODE_W - 1 : `SNT_CTRL_MODE_LSB];
    assign c3_on      = ctrl[`SNT_CTRL_C3_EN_LSB];
    assign trust_csum = ctrl[`SNT_CTRL_TRUST_CSUM_LANE_LSB];
    assign img_sel    = ctrl[`SNT_CTRL_IMG_SEL_LSB];

    assign gov_auto       = gov_ctrl[`SNT_GOV_CTRL_AUTO_LSB];
    assign gov_level      = gov_ctrl[`SNT_GOV_CTRL_LEVEL_LSB + 3 : `SNT_GOV_CTRL_LEVEL_LSB];
    assign gov_turbo_mask = gov_ctrl[`SNT_GOV_CTRL_TURBO_MASK_LSB + 7 : `SNT_GOV_CTRL_TURBO_MASK_LSB];
    assign gov_n_up       = gov_param[`SNT_GOV_PARAM_N_UP_LSB + 7 : `SNT_GOV_PARAM_N_UP_LSB];
    assign gov_cooldown   = gov_param[`SNT_GOV_PARAM_COOLDOWN_LSB + 7 : `SNT_GOV_PARAM_COOLDOWN_LSB];
    assign gov_corr_hi    = gov_param[`SNT_GOV_PARAM_CORR_HI_LSB + 7 : `SNT_GOV_PARAM_CORR_HI_LSB];
    assign gov_l_min      = gov_param[`SNT_GOV_PARAM_L_MIN_LSB + 3 : `SNT_GOV_PARAM_L_MIN_LSB];
    assign gov_l_max      = gov_param[`SNT_GOV_PARAM_L_MAX_LSB + 3 : `SNT_GOV_PARAM_L_MAX_LSB];
    assign clk_reconfig_level = clk_ctrl[`SNT_CLK_CTRL_LEVEL_LSB + 3 : `SNT_CLK_CTRL_LEVEL_LSB];

    assign inj_en      = {inj1_ctrl[`SNT_INJ1_CTRL_EN_LSB], inj0_ctrl[`SNT_INJ0_CTRL_EN_LSB]};
    assign inj_any     = {inj1_ctrl[`SNT_INJ1_CTRL_ANY_LSB], inj0_ctrl[`SNT_INJ0_CTRL_ANY_LSB]};
    assign inj_oneshot = {inj1_ctrl[`SNT_INJ1_CTRL_ONESHOT_LSB], inj0_ctrl[`SNT_INJ0_CTRL_ONESHOT_LSB]};
    assign inj_layer   = {inj1_ctrl[`SNT_INJ1_CTRL_LAYER_LSB + 3 : `SNT_INJ1_CTRL_LAYER_LSB],
                          inj0_ctrl[`SNT_INJ0_CTRL_LAYER_LSB + 3 : `SNT_INJ0_CTRL_LAYER_LSB]};
    assign inj_lane    = {inj1_ctrl[`SNT_INJ1_CTRL_LANE_LSB + 5 : `SNT_INJ1_CTRL_LANE_LSB],
                          inj0_ctrl[`SNT_INJ0_CTRL_LANE_LSB + 5 : `SNT_INJ0_CTRL_LANE_LSB]};
    assign inj_unit    = {inj1_unit[15:0], inj0_unit[15:0]};
    assign inj_mask    = {inj1_mask_hi[15:0], inj1_mask_lo, inj0_mask_hi[15:0], inj0_mask_lo};

    function [31:0] with_byte;
        input [31:0] old;
        input [1:0]  idx;
        input [7:0]  value;
        begin
            with_byte = old;
            with_byte[idx*8 +: 8] = value;
        end
    endfunction

    wire [7:0] pulse_mask_ctrl = (8'd1 << `SNT_CTRL_START_LSB) | (8'd1 << `SNT_CTRL_SOFT_RESET_LSB);

    always @(posedge clk) begin
        start              <= 1'b0;
        soft_reset         <= 1'b0;
        clk_reconfig_start <= 1'b0;
        gov_init           <= 1'b0;
        if (rst) begin
            ctrl         <= 32'd0;
            gov_ctrl     <= 32'd0;
            gov_param    <= 32'd0;
            clk_ctrl     <= 32'd0;
            inj0_ctrl    <= 32'd0;
            inj0_unit    <= 32'd0;
            inj0_mask_lo <= 32'd0;
            inj0_mask_hi <= 32'd0;
            inj1_ctrl    <= 32'd0;
            inj1_unit    <= 32'd0;
            inj1_mask_lo <= 32'd0;
            inj1_mask_hi <= 32'd0;
        end else if (bus_wr) begin
            case (word_addr)
                `SNT_REG_CTRL: begin
                    if (byte_idx == 2'd0) begin
                        ctrl[7:0]  <= bus_wdata & ~pulse_mask_ctrl;
                        start      <= bus_wdata[`SNT_CTRL_START_LSB];
                        soft_reset <= bus_wdata[`SNT_CTRL_SOFT_RESET_LSB];
                    end
                end
                `SNT_REG_GOV_CTRL: begin
                    gov_ctrl <= with_byte(gov_ctrl, byte_idx, bus_wdata);
                    if (byte_idx == 2'd0) gov_init <= bus_wdata[`SNT_GOV_CTRL_INIT_LSB];
                end
                `SNT_REG_GOV_PARAM: gov_param <= with_byte(gov_param, byte_idx, bus_wdata);
                `SNT_REG_CLK_CTRL: begin
                    clk_ctrl <= with_byte(clk_ctrl, byte_idx, bus_wdata);
                    if (byte_idx == 2'd0) clk_reconfig_start <= bus_wdata[`SNT_CLK_CTRL_RECONFIG_START_LSB];
                end
                `SNT_REG_INJ0_CTRL:    inj0_ctrl    <= with_byte(inj0_ctrl, byte_idx, bus_wdata);
                `SNT_REG_INJ0_UNIT:    inj0_unit    <= with_byte(inj0_unit, byte_idx, bus_wdata);
                `SNT_REG_INJ0_MASK_LO: inj0_mask_lo <= with_byte(inj0_mask_lo, byte_idx, bus_wdata);
                `SNT_REG_INJ0_MASK_HI: inj0_mask_hi <= with_byte(inj0_mask_hi, byte_idx, bus_wdata);
                `SNT_REG_INJ1_CTRL:    inj1_ctrl    <= with_byte(inj1_ctrl, byte_idx, bus_wdata);
                `SNT_REG_INJ1_UNIT:    inj1_unit    <= with_byte(inj1_unit, byte_idx, bus_wdata);
                `SNT_REG_INJ1_MASK_LO: inj1_mask_lo <= with_byte(inj1_mask_lo, byte_idx, bus_wdata);
                `SNT_REG_INJ1_MASK_HI: inj1_mask_hi <= with_byte(inj1_mask_hi, byte_idx, bus_wdata);
                default: ;
            endcase
        end
    end

    // ---- read path ----------------------------------------------------------------------
    reg [31:0] read_mux;
    localparam [7:0] VER_MAJOR = `SNT_VER_MAJOR;
    localparam [7:0] VER_MINOR = `SNT_VER_MINOR;
    wire [31:0] version = {16'd0, VER_MAJOR, VER_MINOR};

    always @* begin
        read_mux = 32'd0;
        case (word_addr)
            `SNT_REG_ID:               read_mux = 32'h534E544C;
            `SNT_REG_VERSION:          read_mux = version;
            `SNT_REG_CTRL:             read_mux = ctrl;
            `SNT_REG_STATUS:           read_mux = {26'd0, fast_is_turbo, mmcm2_locked, log_ovf, fatal, done_flag, busy};
            `SNT_REG_RESULT_CLASS:     read_mux = {28'd0, result_class};
            `SNT_REG_CYCLES_TOTAL:     read_mux = cycles_total;
            `SNT_REG_CYCLES_RECOMPUTE: read_mux = cycles_recompute;
            `SNT_REG_STARVE_CYCLES:    read_mux = starve_cycles;
            `SNT_REG_GOV_CTRL:         read_mux = gov_ctrl;
            `SNT_REG_GOV_PARAM:        read_mux = gov_param;
            `SNT_REG_GOV_STATE:        read_mux = {8'd0, gov_state_turbo, gov_state_streak, 4'd0, gov_state_level};
            `SNT_REG_CLK_CTRL:         read_mux = clk_ctrl;
            `SNT_REG_CLK_STATUS:       read_mux = {30'd0, clk_locked, clk_reconfig_busy};
            `SNT_REG_INJ0_CTRL:        read_mux = inj0_ctrl;
            `SNT_REG_INJ0_UNIT:        read_mux = inj0_unit;
            `SNT_REG_INJ0_MASK_LO:     read_mux = inj0_mask_lo;
            `SNT_REG_INJ0_MASK_HI:     read_mux = inj0_mask_hi;
            `SNT_REG_INJ1_CTRL:        read_mux = inj1_ctrl;
            `SNT_REG_INJ1_UNIT:        read_mux = inj1_unit;
            `SNT_REG_INJ1_MASK_LO:     read_mux = inj1_mask_lo;
            `SNT_REG_INJ1_MASK_HI:     read_mux = inj1_mask_hi;
            `SNT_REG_LANE_STATUS:      read_mux = lane_status;
            `SNT_REG_TEMP:             read_mux = temp;
            default:                   read_mux = 32'd0;
        endcase
        if (is_counter) read_mux = cnt_data;
    end

    reg [31:0] latched;
    wire [31:0] source = (byte_idx == 2'd0) ? read_mux : latched;

    always @(posedge clk) begin
        if (bus_rd) begin
            if (byte_idx == 2'd0) latched <= read_mux;
            bus_rdata <= source[byte_idx*8 +: 8];
        end
    end

    wire unused_regfile = &{1'b0, inj0_ctrl[31:14], inj1_ctrl[31:14], inj0_ctrl[3], inj1_ctrl[3], inj0_unit[31:16],
                            inj1_unit[31:16], inj0_mask_hi[31:16], inj1_mask_hi[31:16], word_addr[11:2], ctrl[31:8],
                            ctrl[1:0], ctrl[7], gov_ctrl[31:24], gov_ctrl[15:12], gov_ctrl[7:1], clk_ctrl[31:12], clk_ctrl[7:0]};
endmodule

`default_nettype wire
