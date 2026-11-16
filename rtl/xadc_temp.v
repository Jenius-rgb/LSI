`timescale 1ns / 1ps
`default_nettype none

// On-chip temperature (ADR-018, ADR-023).  Reads XADC status register 00h over the DRP every
// 2^POLL_LOG2 clock cycles and keeps its 12 MSBs.  The XADC set-up (continuous sequence of the
// calibration and temperature channels, DCLK / 8) is in rtl/platform/xilinx/xadc_prim_xilinx.v.
// Degrees Celsius = code * 503.975 / 4096 - 273.15 (UG480 Equation 2-6), computed by the host.
module xadc_temp #(
    parameter        POLL_LOG2 = 20,        // about 8 ms at 125 MHz
    parameter [11:0] SIM_CODE  = 12'd2423   // behavioural model only
) (
    input  wire        clk,
    input  wire        rst,
    output reg  [11:0] code,
    output reg         valid
);
    reg         den;
    wire [6:0]  daddr = 7'h00;
    wire [15:0] dout;
    wire        drdy;

`ifdef SENTINEL_XILINX
    xadc_prim_xilinx u_xadc (
        .dclk(clk), .reset(rst), .den(den), .daddr(daddr), .dout(dout), .drdy(drdy));
`else
    xadc_prim_sim #(.CODE(SIM_CODE)) u_xadc (
        .dclk(clk), .reset(rst), .den(den), .daddr(daddr), .dout(dout), .drdy(drdy));
`endif

    wire unused_lsbs = &{1'b0, dout[3:0]};   // status registers are MSB justified (UG480 Table 3-1)

    reg [POLL_LOG2-1:0] timer;
    reg                 waiting;
    reg [9:0]           timeout;

    always @(posedge clk) begin
        den <= 1'b0;
        if (rst) begin
            timer   <= {POLL_LOG2{1'b0}};
            waiting <= 1'b0;
            timeout <= 10'd0;
            code    <= 12'd0;
            valid   <= 1'b0;
        end else if (waiting) begin
            timeout <= timeout + 1'b1;
            if (drdy) begin
                code    <= dout[15:4];
                valid   <= 1'b1;
                waiting <= 1'b0;
            end else if (&timeout) begin
                waiting <= 1'b0;   // no answer: try again at the next poll
            end
        end else begin
            timer <= timer + 1'b1;
            if (timer == {{(POLL_LOG2-1){1'b0}}, 1'b1}) begin
                den     <= 1'b1;
                waiting <= 1'b1;
                timeout <= 10'd0;
            end
        end
    end
endmodule

`default_nettype wire
