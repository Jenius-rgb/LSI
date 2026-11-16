`timescale 1ns / 1ps
`default_nettype none

// Status colour on the FPGA-driven WS2812B (LED1, pin N1; ADR-017), in GRB order at low brightness:
//   FATAL red, busy in turbo magenta, busy blue, done green, idle dim white.
// A frame is sent when the colour changes and every 2^REFRESH_LOG2 clocks.
// The pulse timing (T0H 400 ns, T1H 800 ns, bit 1250 ns, latch low 300 us) is the commonly published
// WS2812B timing and has NOT been checked against the data sheet of the LED on ZERO7 [UNKNOWN part];
// 300 us covers both the 50 us and the 280 us latch times seen in WS2812B variants.
module status_led #(
    parameter CLK_HZ       = 125_000_000,
    parameter REFRESH_LOG2 = 20
) (
    input  wire clk,
    input  wire rst,
    input  wire fatal,
    input  wire is_turbo,
    input  wire done,
    input  wire busy,
    output wire dout
);
    localparam integer CYC_PER_US = CLK_HZ / 1_000_000;
    localparam integer T0H_CYC    = CYC_PER_US * 400 / 1000;
    localparam integer T1H_CYC    = CYC_PER_US * 800 / 1000;
    localparam integer BIT_CYC    = CYC_PER_US * 1250 / 1000;
    localparam integer RESET_CYC  = CYC_PER_US * 300;

    wire [23:0] colour = fatal             ? 24'h00_20_00 :   // G, R, B
                         (busy & is_turbo) ? 24'h00_20_20 :
                         busy              ? 24'h00_00_20 :
                         done              ? 24'h20_00_00 :
                                             24'h04_04_04;

    reg  [23:0]             sent;
    reg  [REFRESH_LOG2-1:0] timer;
    reg                     tx_start;
    wire                    tx_busy;

    always @(posedge clk) begin
        tx_start <= 1'b0;
        if (rst) begin
            sent  <= 24'hFFFFFF;   // forces a first frame after reset
            timer <= {REFRESH_LOG2{1'b0}};
        end else begin
            timer <= timer + 1'b1;
            if (!tx_busy && !tx_start && (colour != sent || &timer)) begin
                tx_start <= 1'b1;
                sent     <= colour;
            end
        end
    end

    ws2812_tx #(.T0H_CYC(T0H_CYC), .T1H_CYC(T1H_CYC), .BIT_CYC(BIT_CYC), .RESET_CYC(RESET_CYC)) u_tx (
        .clk(clk), .rst(rst), .start(tx_start), .grb(sent), .dout(dout), .busy(tx_busy));
endmodule

`default_nettype wire
