`timescale 1ns / 1ps
`default_nettype none

// AXI4-Lite master driven from the PC over JTAG (ADR-025): the AMD JTAG-to-AXI Master IP under
// Vivado, a log-replay model in simulation.
module jtag_axi_master (
    input  wire        clk,
    input  wire        rst,
    output wire [31:0] m_awaddr,
    output wire        m_awvalid,
    input  wire        m_awready,
    output wire [31:0] m_wdata,
    output wire [3:0]  m_wstrb,
    output wire        m_wvalid,
    input  wire        m_wready,
    input  wire [1:0]  m_bresp,
    input  wire        m_bvalid,
    output wire        m_bready,
    output wire [31:0] m_araddr,
    output wire        m_arvalid,
    input  wire        m_arready,
    input  wire [31:0] m_rdata,
    input  wire [1:0]  m_rresp,
    input  wire        m_rvalid,
    output wire        m_rready
);
`ifdef SENTINEL_XILINX
    jtag_axi_master_xilinx u_m (
`else
    jtag_axi_master_sim u_m (
`endif
        .clk(clk), .rst(rst),
        .m_awaddr(m_awaddr), .m_awvalid(m_awvalid), .m_awready(m_awready), .m_wdata(m_wdata), .m_wstrb(m_wstrb),
        .m_wvalid(m_wvalid), .m_wready(m_wready), .m_bresp(m_bresp), .m_bvalid(m_bvalid), .m_bready(m_bready),
        .m_araddr(m_araddr), .m_arvalid(m_arvalid), .m_arready(m_arready), .m_rdata(m_rdata), .m_rresp(m_rresp),
        .m_rvalid(m_rvalid), .m_rready(m_rready));
endmodule

`default_nettype wire
