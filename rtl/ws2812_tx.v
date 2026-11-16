`timescale 1ns / 1ps
`default_nettype none

// WS2812B serial transmitter (ADR-017).  Sends one 24-bit GRB word, MSB first: each bit is high for
// T1H_CYC (one) or T0H_CYC (zero) clocks and lasts BIT_CYC clocks; then the line stays low for
// RESET_CYC clocks so the LED latches the word.  The cycle counts come from status_led.v.
module ws2812_tx #(
    parameter T0H_CYC   = 50,
    parameter T1H_CYC   = 100,
    parameter BIT_CYC   = 156,
    parameter RESET_CYC = 37500
) (
    input  wire        clk,
    input  wire        rst,
    input  wire        start,
    input  wire [23:0] grb,
    output reg         dout,
    output wire        busy
);
    localparam [1:0] S_IDLE = 2'd0, S_BIT = 2'd1, S_RESET = 2'd2;
    reg [1:0]  state;
    reg [23:0] shift;
    reg [4:0]  nbit;
    reg [17:0] cnt;

    assign busy = (state != S_IDLE);

    always @(posedge clk) begin
        if (rst) begin
            state <= S_IDLE;
            dout  <= 1'b0;
            shift <= 24'd0;
            nbit  <= 5'd0;
            cnt   <= 18'd0;
        end else begin
            case (state)
                S_IDLE: begin
                    dout <= 1'b0;
                    if (start) begin
                        shift <= grb;
                        nbit  <= 5'd0;
                        cnt   <= 18'd0;
                        dout  <= 1'b1;
                        state <= S_BIT;
                    end
                end
                S_BIT: begin
                    cnt <= cnt + 1'b1;
                    if (cnt + 1 == (shift[23] ? T1H_CYC : T0H_CYC)) dout <= 1'b0;
                    if (cnt + 1 == BIT_CYC) begin
                        cnt   <= 18'd0;
                        shift <= {shift[22:0], 1'b0};
                        nbit  <= nbit + 1'b1;
                        if (nbit == 5'd23) begin
                            dout  <= 1'b0;
                            state <= S_RESET;
                        end else begin
                            dout <= 1'b1;
                        end
                    end
                end
                S_RESET: begin
                    dout <= 1'b0;
                    cnt  <= cnt + 1'b1;
                    if (cnt + 1 == RESET_CYC) state <= S_IDLE;
                end
                default: state <= S_IDLE;
            endcase
        end
    end
endmodule

`default_nettype wire
