`timescale 1ns / 1ps
`default_nettype none

// Bring-up: SPI path from the Raspberry Pi 5 (SPI0, CE0) to the FPGA, SPI mode 0, MSB first.
// Within one chip-select assertion the FPGA returns 0xA5 for the first byte, then every byte it received, one
// byte late: send b0 b1 ... bn, receive A5 b0 ... b(n-1).  board/spi_loopback_check.py runs this on the Pi.
// SCLK, MOSI and CE0 are oversampled with CLK20M behind two-flop synchronizers, so SCLK must stay at or below
// f_clk / 8 = 2.5 MHz for a 20 MHz clock [INFERENCE: same rule as SPEC 12.1].
// MISO (A7) is shared with the Pi's GPIO9, which is an input on the Pi while SPI0 is enabled; the FPGA drives it
// only while CE0 is low and releases it (high impedance) otherwise.
// LED1 (R3) toggles on every received byte; LED2 (R2) lights while CE0 is low (polarity of the LEDs UNKNOWN).
// No reset input: the registers start from their FPGA configuration values (initial blocks), as in blink_top.
module spi_loopback_top #(
    parameter [7:0] FIRST = 8'hA5
) (
    input  wire clk_in,      // CLK20M, B13
    input  wire spi_sclk,    // RP_GPIO11 SCLK, A8 (JP11 "(CUT)" on this line, TK-1)
    input  wire spi_mosi,    // RP_GPIO10 MOSI, A6 (JP9 "(CUT)" on this line, TK-1)
    input  wire spi_cs_n,    // RP_GPIO8 CE0, D9
    output wire spi_miso,    // RP_GPIO9 MISO, A7
    output reg  led1,        // GPIO_LED1, R3
    output wire led2         // GPIO_LED2, R2
);
    (* ASYNC_REG = "TRUE" *) reg [1:0] sclk_meta, mosi_meta, cs_meta;
    reg       sclk_d, cs_d;
    reg [7:0] rx_sh, tx_sh;
    reg [2:0] bit_cnt;
    reg       load_next;

    initial begin
        sclk_meta = 2'b00; mosi_meta = 2'b00; cs_meta = 2'b11;
        sclk_d = 1'b0; cs_d = 1'b1;
        rx_sh = 8'd0; tx_sh = FIRST; bit_cnt = 3'd0; load_next = 1'b0; led1 = 1'b0;
    end

    wire sclk_s   = sclk_meta[1];
    wire mosi_s   = mosi_meta[1];
    wire cs_n_s   = cs_meta[1];
    wire sclk_up  = sclk_s & ~sclk_d;
    wire sclk_dn  = ~sclk_s & sclk_d;
    wire cs_start = ~cs_n_s & cs_d;

    always @(posedge clk_in) begin
        sclk_meta <= {sclk_meta[0], spi_sclk};
        mosi_meta <= {mosi_meta[0], spi_mosi};
        cs_meta   <= {cs_meta[0], spi_cs_n};
        sclk_d    <= sclk_s;
        cs_d      <= cs_n_s;
        if (cs_start) begin
            tx_sh     <= FIRST;
            bit_cnt   <= 3'd0;
            load_next <= 1'b0;
        end else if (!cs_n_s) begin
            if (sclk_up) begin
                rx_sh   <= {rx_sh[6:0], mosi_s};
                bit_cnt <= bit_cnt + 3'd1;
                if (bit_cnt == 3'd7) begin
                    load_next <= 1'b1;
                    led1      <= ~led1;
                end
            end
            if (sclk_dn) begin
                if (load_next) begin
                    tx_sh     <= rx_sh;          // the byte completed on the previous rising edge
                    load_next <= 1'b0;
                end else begin
                    tx_sh     <= {tx_sh[6:0], 1'b0};
                end
            end
        end
    end

    assign spi_miso = cs_n_s ? 1'bz : tx_sh[7];
    assign led2     = ~cs_n_s;
endmodule

`default_nettype wire
