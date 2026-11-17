`timescale 1ns / 1ps
`default_nettype none

// ADR-025: top_jtag with the log-replay model of the JTAG-to-AXI master (rtl/platform/sim/jtag_axi_master_sim.v).
// The model reads +log, checks every read against the Python device model and prints PASS or FAIL.
module tb_jtag_log;
    parameter K = 8;
    parameter C3_EN = 0;
    parameter WEIGHT_AW = 11;
    parameter ACT0_AW = 12;
    parameter ACT1_AW = 10;
    reg clk_in = 1'b0;
    always #25 clk_in = ~clk_in;     // CLK20M; the simulation clock generator makes clk_safe itself
    wire led_busy, led_fatal, ws2812_dout;
    top_jtag #(.K(K), .C3_EN(C3_EN), .WEIGHT_AW(WEIGHT_AW), .ACT0_AW(ACT0_AW), .ACT1_AW(ACT1_AW)) dut (
        .clk_in(clk_in), .led_busy(led_busy), .led_fatal(led_fatal), .ws2812_dout(ws2812_dout));
endmodule

`default_nettype wire
