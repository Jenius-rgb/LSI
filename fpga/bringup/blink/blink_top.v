`timescale 1ns / 1ps
`default_nettype none

// Bring-up step 1 without the Raspberry Pi (ADR-026): blink the two FPGA-only LEDs from CLK20M.
// LED1 (D5, pin R3) toggles every HALF clocks and LED2 (D6, pin R2) is its inverse, so the LEDs
// alternate whatever their polarity.  With HALF = 10_000_000 and a 20 MHz clock [OFFICIAL: B13,
// "Clock (20MHz, 3.3V)"] one full period is 2 * HALF / f = 1.000 s.  Measured clock:
//   f_clk = 2 * HALF * n_periods / t_measured    (count n_periods full periods over t_measured seconds)
module blink_top #(
    parameter HALF = 10_000_000
) (
    input  wire clk_in,     // CLK20M, B13
    output reg  led1,       // GPIO_LED1, R3
    output wire led2        // GPIO_LED2, R2
);
    reg [31:0] count;
    initial begin
        count = 32'd0;
        led1  = 1'b0;
    end
    always @(posedge clk_in) begin
        if (count == HALF - 1) begin
            count <= 32'd0;
            led1  <= ~led1;
        end else begin
            count <= count + 1'b1;
        end
    end
    assign led2 = ~led1;
endmodule

`default_nettype wire
