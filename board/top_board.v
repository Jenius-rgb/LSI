`timescale 1ns / 1ps
`default_nettype none

// Board top level for ZERO7.  Port meaning is fixed; pin numbers live in the XDC and stay
// unassigned until board/BOARD_INFO.md has them.
module top_board #(
    parameter K         = 8,
    parameter C3_EN     = 0,
    parameter LANE_IMPL = 0
) (
    input  wire       clk_in,
    input  wire       spi_sclk,
    input  wire       spi_cs_n,
    input  wire       spi_mosi,
    output wire       spi_miso,
    output wire [3:0] led
);
    // Power-on reset; a real board may add a push button here once its pin is known.
    reg [7:0] por = 8'hFF;
    always @(posedge clk_in) por <= {por[6:0], 1'b0};

    top_core #(.K(K), .C3_EN(C3_EN), .LANE_IMPL(LANE_IMPL)) u_core (
        .clk_in(clk_in), .rst(por[7]),
        .spi_sclk(spi_sclk), .spi_cs_n(spi_cs_n), .spi_mosi(spi_mosi), .spi_miso(spi_miso),
        .led(led));
endmodule

`default_nettype wire
