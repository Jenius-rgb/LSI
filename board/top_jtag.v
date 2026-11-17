`timescale 1ns / 1ps
`default_nettype none

// ZERO7 without the Raspberry Pi (ADR-025, ADR-026): the full SENTINEL core with the PC as host over
// the JTAG cable.  JTAG-to-AXI master -> axil_bus_bridge -> host byte bus of top_core.  The SPI port is
// tied idle and its pins are not used, so no line shared with the Pi header is driven.
module top_jtag #(
    parameter K         = 8,
    parameter C3_EN     = 1,
    parameter LANE_IMPL = 0,
    parameter WEIGHT_AW = 12,
    parameter ACT0_AW   = 13,
    parameter ACT1_AW   = 11
) (
    input  wire clk_in,      // CLK20M, B13
    output wire led_busy,    // D5
    output wire led_fatal,   // D6
    output wire ws2812_dout  // N1
);
    reg [7:0] por;
    initial por = 8'hFF;
    always @(posedge clk_in) por <= {por[6:0], 1'b0};

    wire [3:0]  status;
    wire        ext_wr, ext_rd, host_rvalid, clk_safe, rst_safe;
    wire [23:0] ext_addr;
    wire [7:0]  ext_wdata, host_rdata;
    wire [63:0] id_word;
    wire        spi_miso_unused;

    top_core #(
        .K(K), .C3_EN(C3_EN), .LANE_IMPL(LANE_IMPL),
        .WEIGHT_AW(WEIGHT_AW), .ACT0_AW(ACT0_AW), .ACT1_AW(ACT1_AW)
    ) u_core (
        .clk_in(clk_in), .rst(por[7]),
        .spi_sclk(1'b0), .spi_cs_n(1'b1), .spi_mosi(1'b0), .spi_miso(spi_miso_unused),
        .led(status), .ws2812(ws2812_dout),
        .ext_wr(ext_wr), .ext_rd(ext_rd), .ext_addr(ext_addr), .ext_wdata(ext_wdata),
        .host_rdata(host_rdata), .host_rvalid(host_rvalid), .clk_safe_o(clk_safe), .rst_safe_o(rst_safe), .id_word_o(id_word));

    wire [31:0] awaddr, wdata, araddr, rdata;
    wire [3:0]  wstrb;
    wire [1:0]  bresp, rresp;
    wire        awvalid, awready, wvalid, wready, bvalid, bready, arvalid, arready, rvalid, rready;

    jtag_axi_master u_jtag (
        .clk(clk_safe), .rst(rst_safe),
        .m_awaddr(awaddr), .m_awvalid(awvalid), .m_awready(awready), .m_wdata(wdata), .m_wstrb(wstrb),
        .m_wvalid(wvalid), .m_wready(wready), .m_bresp(bresp), .m_bvalid(bvalid), .m_bready(bready),
        .m_araddr(araddr), .m_arvalid(arvalid), .m_arready(arready), .m_rdata(rdata), .m_rresp(rresp),
        .m_rvalid(rvalid), .m_rready(rready));

    axil_bus_bridge u_bridge (
        .clk(clk_safe), .rst(rst_safe),
        .s_awaddr(awaddr), .s_awvalid(awvalid), .s_awready(awready), .s_wdata(wdata), .s_wstrb(wstrb),
        .s_wvalid(wvalid), .s_wready(wready), .s_bresp(bresp), .s_bvalid(bvalid), .s_bready(bready),
        .s_araddr(araddr), .s_arvalid(arvalid), .s_arready(arready), .s_rdata(rdata), .s_rresp(rresp),
        .s_rvalid(rvalid), .s_rready(rready),
        .bus_wr(ext_wr), .bus_rd(ext_rd), .bus_addr(ext_addr), .bus_wdata(ext_wdata),
        .bus_rdata(host_rdata), .bus_rvalid(host_rvalid), .id_word(id_word));

    assign led_busy  = status[0];
    assign led_fatal = status[3];
    wire unused = &{1'b0, status[2:1], spi_miso_unused};
endmodule

`default_nettype wire
