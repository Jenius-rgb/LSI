`timescale 1ns / 1ps
`default_nettype none

// Xilinx clock generation (SPEC 7.6, ADR-015).  MMCM1 makes clk_safe, MMCM2 makes clk_turbo,
// BUFGCTRL muxes them into clk_fast.  Only used under Vivado.
//
// The board clock is 20 MHz on pin B13 (board/BOARD_INFO.md).  Both MMCMs run their VCO at
// F_IN * MULT = 1000 MHz.  The MMCM limits in config/mmcm_limits.yaml have not been checked
// against DS189 yet; Vivado's DRC is the interim check.  MMCM2 starts at the safe frequency
// (turbo level 0).  The DRP write sequencer that changes it (ADR-010) does not exist yet, so
// reconfig_start is ignored and the turbo clock keeps its initial frequency.
//
// The safe divider can be set at synthesis time with -verilog_define SENTINEL_SAFE_DIV=10.0
// (100 MHz) when 125 MHz does not meet timing.
`ifndef SENTINEL_SAFE_DIV
`define SENTINEL_SAFE_DIV 8.0
`endif

module clk_gen_xilinx #(
    parameter LEVELS_LOG2 = 4,
    parameter real CLKIN_PERIOD = 50.0,                 // 20 MHz
    parameter real SAFE_MULT    = 50.0,                 // VCO 1000 MHz
    parameter real SAFE_DIV     = `SENTINEL_SAFE_DIV,   // clk_safe = 1000 / SAFE_DIV MHz
    parameter real TURBO_MULT   = 50.0,
    parameter real TURBO_DIV    = `SENTINEL_SAFE_DIV    // turbo level 0 equals the safe frequency
) (
    input  wire                   clk_in,
    input  wire                   rst,
    output wire                   clk_safe,
    output wire                   clk_fast,
    output wire                   locked,
    input  wire                   sel_turbo,
    output wire                   is_turbo,
    input  wire                   reconfig_start,
    input  wire [LEVELS_LOG2-1:0] reconfig_level,
    output wire                   reconfig_busy,
    output wire                   turbo_locked
);
    wire clk_safe_raw, clk_turbo_raw, safe_fb, turbo_fb, safe_fb_buf, turbo_fb_buf;
    wire locked1, locked2;
    wire clk_safe_buf, clk_turbo_buf;

    MMCME2_BASE #(
        .CLKIN1_PERIOD(CLKIN_PERIOD), .CLKFBOUT_MULT_F(SAFE_MULT), .CLKOUT0_DIVIDE_F(SAFE_DIV), .DIVCLK_DIVIDE(1)
    ) u_mmcm1 (
        .CLKIN1(clk_in), .CLKFBIN(safe_fb_buf), .RST(rst), .PWRDWN(1'b0),
        .CLKFBOUT(safe_fb), .CLKFBOUTB(), .CLKOUT0(clk_safe_raw), .CLKOUT0B(), .CLKOUT1(), .CLKOUT1B(),
        .CLKOUT2(), .CLKOUT2B(), .CLKOUT3(), .CLKOUT3B(), .CLKOUT4(), .CLKOUT5(), .CLKOUT6(), .LOCKED(locked1));

    BUFG u_fb1 (.I(safe_fb), .O(safe_fb_buf));
    BUFG u_safe (.I(clk_safe_raw), .O(clk_safe_buf));

    MMCME2_ADV #(
        .CLKIN1_PERIOD(CLKIN_PERIOD), .CLKFBOUT_MULT_F(TURBO_MULT), .CLKOUT0_DIVIDE_F(TURBO_DIV), .DIVCLK_DIVIDE(1)
    ) u_mmcm2 (
        .CLKIN1(clk_in), .CLKIN2(1'b0), .CLKINSEL(1'b1), .CLKFBIN(turbo_fb_buf), .RST(rst), .PWRDWN(1'b0),
        .CLKFBOUT(turbo_fb), .CLKFBOUTB(), .CLKOUT0(clk_turbo_raw), .CLKOUT0B(), .CLKOUT1(), .CLKOUT1B(),
        .CLKOUT2(), .CLKOUT2B(), .CLKOUT3(), .CLKOUT3B(), .CLKOUT4(), .CLKOUT5(), .CLKOUT6(),
        .DADDR(7'd0), .DCLK(clk_safe_buf), .DEN(1'b0), .DI(16'd0), .DWE(1'b0), .DO(), .DRDY(),
        .PSCLK(1'b0), .PSEN(1'b0), .PSINCDEC(1'b0), .PSDONE(), .LOCKED(locked2),
        .CLKINSTOPPED(), .CLKFBSTOPPED());

    BUFG u_fb2 (.I(turbo_fb), .O(turbo_fb_buf));
    BUFG u_turbo (.I(clk_turbo_raw), .O(clk_turbo_buf));

    BUFGCTRL #(.INIT_OUT(0), .PRESELECT_I0("TRUE"), .PRESELECT_I1("FALSE")) u_mux (
        .I0(clk_safe_buf), .I1(clk_turbo_buf), .S0(~sel_turbo), .S1(sel_turbo),
        .CE0(1'b1), .CE1(1'b1), .IGNORE0(1'b0), .IGNORE1(1'b0), .O(clk_fast));

    assign clk_safe      = clk_safe_buf;
    assign locked        = locked1;
    assign turbo_locked  = locked2;
    // No DRP sequencer yet: no reconfiguration, and the selection is reported as requested.
    assign is_turbo      = sel_turbo;
    assign reconfig_busy = 1'b0;

    wire unused_reconfig = &{1'b0, reconfig_start, reconfig_level};
endmodule

`default_nettype wire
