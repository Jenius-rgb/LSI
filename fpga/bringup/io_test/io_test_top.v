`timescale 1ns / 1ps
`default_nettype none

// Bring-up step 3 without the Raspberry Pi (ADR-026): show the buttons and switches on the LEDs.
//   LED1 (R3) = SW1 / PSW (R4), LED2 (R2) = SW3 / DIP (M4), both as raw levels.
//   WS2812B LED1 (N1), GRB at low brightness: red = START (C14), green = STOP (B15), blue = RUN (C13), raw levels.
// The button polarity and pull resistors are [UNKNOWN]: record which level a press gives.  START, STOP and
// RUN share their lines with the Raspberry Pi header (RP_GPIO20, 21, 16), so the FPGA only reads them.
// Clocked directly from CLK20M (20 MHz): at 50 ns per clock the WS2812B timing is T0H 8, T1H 16,
// bit 25 clocks (400 ns, 800 ns, 1.25 us) and a 300 us latch gap (6000 clocks); the timing is the
// commonly published WS2812B timing, not checked against the data sheet of the LED on ZERO7.
module io_test_top #(
    parameter T0H_CYC      = 8,
    parameter T1H_CYC      = 16,
    parameter BIT_CYC      = 25,
    parameter RESET_CYC    = 6000,
    parameter REFRESH_LOG2 = 18      // a frame about every 13 ms
) (
    input  wire clk_in,
    input  wire btn_start,
    input  wire btn_stop,
    input  wire btn_run,
    input  wire btn_psw,
    input  wire dip_sw,
    output wire led1,
    output wire led2,
    output wire ws2812_dout
);
    // Two-flop synchronizers for the asynchronous inputs (SPEC 7.8 style).
    (* ASYNC_REG = "TRUE" *) reg [4:0] in_meta;
    (* ASYNC_REG = "TRUE" *) reg [4:0] in_sync;
    initial begin
        in_meta = 5'd0;
        in_sync = 5'd0;
    end
    always @(posedge clk_in) begin
        in_meta <= {dip_sw, btn_psw, btn_run, btn_stop, btn_start};
        in_sync <= in_meta;
    end
    assign led1 = in_sync[3];
    assign led2 = in_sync[4];

    wire [23:0] colour = {in_sync[1] ? 8'h20 : 8'h00,    // G = STOP
                          in_sync[0] ? 8'h20 : 8'h00,    // R = START
                          in_sync[2] ? 8'h20 : 8'h00};   // B = RUN

    reg [REFRESH_LOG2-1:0] timer;
    reg                    tx_start;
    reg                    rst_tx;
    wire                   tx_busy;
    initial begin
        timer    = {REFRESH_LOG2{1'b0}};
        tx_start = 1'b0;
        rst_tx   = 1'b1;
    end
    always @(posedge clk_in) begin
        rst_tx   <= 1'b0;
        timer    <= timer + 1'b1;
        tx_start <= (&timer) & ~tx_busy;
    end

    ws2812_tx #(.T0H_CYC(T0H_CYC), .T1H_CYC(T1H_CYC), .BIT_CYC(BIT_CYC), .RESET_CYC(RESET_CYC)) u_tx (
        .clk(clk_in), .rst(rst_tx), .start(tx_start), .grb(colour), .dout(ws2812_dout), .busy(tx_busy));
endmodule

`default_nettype wire
