`timescale 1ns / 1ps
`default_nettype none

// Board top level for ZERO7 (ADR-016).  Pin numbers are in board/zero7.xdc.  The defaults are
// the official variant of config/hw_zero7.yaml: model s, K = 8, lut lanes, C3 on.
module top_board #(
    parameter K         = 8,
    parameter C3_EN     = 1,
    parameter LANE_IMPL = 0,
    parameter WEIGHT_AW = 12,
    parameter ACT0_AW   = 13,
    parameter ACT1_AW   = 11
) (
    input  wire clk_in,      // CLK20M, 20 MHz
    input  wire spi_sclk,    // RP_GPIO11
    input  wire spi_cs_n,    // RP_GPIO8, CE0
    input  wire spi_mosi,    // RP_GPIO10
    output wire spi_miso,    // RP_GPIO9
    output wire led_busy,    // D5
    output wire led_fatal,   // D6
    output wire irq_done,    // RP_GPIO25, high while STATUS.DONE is set
    output wire ws2812_dout  // N1, S7_LED0: WS2812B LED1 status colour (ADR-017)
);
    // Power-on reset from the board clock, before the MMCMs lock.
    reg [7:0] por;
    initial por = 8'hFF;
    always @(posedge clk_in) por <= {por[6:0], 1'b0};

    wire [3:0] status;   // {fatal, is_turbo, done, busy}

    top_core #(
        .K(K), .C3_EN(C3_EN), .LANE_IMPL(LANE_IMPL),
        .WEIGHT_AW(WEIGHT_AW), .ACT0_AW(ACT0_AW), .ACT1_AW(ACT1_AW)
    ) u_core (
        .clk_in(clk_in), .rst(por[7]),
        .spi_sclk(spi_sclk), .spi_cs_n(spi_cs_n), .spi_mosi(spi_mosi), .spi_miso(spi_miso),
        .led(status), .ws2812(ws2812_dout));

    assign led_busy  = status[0];
    assign irq_done  = status[1];
    assign led_fatal = status[3];

    wire unused_turbo = status[2];   // shown as a colour on the WS2812B indicator (ADR-017)
endmodule

`default_nettype wire
