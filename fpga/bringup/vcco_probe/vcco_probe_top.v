`timescale 1ns / 1ps
`default_nettype none

// Bring-up step 2 without the Raspberry Pi (ADR-026): drive known levels so that the I/O bank
// voltages can be measured with a multimeter on the headers.  The VCCO balls of the BGA cannot be
// probed, but an unloaded LVCMOS output high sits at VCCO of its bank.
//   PMOD1 (J1) table pins 1-4 = D15, E15, F15, G15 (bank 15) driven high; table pins 5-8 = E13, E14, F14, G14
//   driven low.  Pin numbers are those of the official connection table; the physical position is [UNKNOWN].
//   N1 (bank 34) = WS2812B data and also J7 [OFFICIAL], driven high (a steady high sends no data).
//   LED1/LED2 alternate as in blink_top so the design is visibly running.
// Only FPGA-only pins are driven; no line shared with the Raspberry Pi header is touched.
module vcco_probe_top #(
    parameter HALF = 10_000_000
) (
    input  wire       clk_in,
    output wire [3:0] pmod1_hi,
    output wire [3:0] pmod1_lo,
    output wire       ws2812_dout,
    output wire       led1,
    output wire       led2
);
    assign pmod1_hi    = 4'hF;
    assign pmod1_lo    = 4'h0;
    assign ws2812_dout = 1'b1;
    blink_top #(.HALF(HALF)) u_blink (.clk_in(clk_in), .led1(led1), .led2(led2));
endmodule

`default_nettype wire
