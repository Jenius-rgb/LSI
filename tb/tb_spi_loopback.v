`timescale 1ns / 1ps
`default_nettype none

// fpga/bringup/spi_loopback against vectors from tools/benches.py (_spi_loopback_vectors).
// SPI mode 0 master: SCLK = 2 MHz from a 20 MHz FPGA clock (the design oversamples, limit clk/8).
// Each frame (one chip-select assertion) must return 0xA5 first, then every byte one position late.
module tb_spi_loopback;
    parameter MAX_BYTES  = 4096;
    parameter MAX_FRAMES = 256;
    parameter HALF_NS    = 250;          // SCLK half period: 2 MHz

    reg clk = 1'b0;
    always #25 clk = ~clk;               // 20 MHz CLK20M

    reg  sclk = 1'b0, mosi = 1'b0, cs_n = 1'b1;
    wire miso, led1, led2;
    spi_loopback_top dut (.clk_in(clk), .spi_sclk(sclk), .spi_mosi(mosi), .spi_cs_n(cs_n), .spi_miso(miso),
                          .led1(led1), .led2(led2));

    reg [7:0]  tx  [0:MAX_BYTES-1];
    reg [7:0]  exp [0:MAX_BYTES-1];
    reg [15:0] len [0:MAX_FRAMES-1];
    reg [1023:0] tx_path, exp_path, len_path;
    integer n_frames, n_bytes, f, i, b, idx, errors;
    reg [7:0] rx;

    task xfer_byte(input [7:0] out, output [7:0] in);
        integer k;
        begin
            for (k = 7; k >= 0; k = k - 1) begin
                mosi = out[k];
                #(HALF_NS) sclk = 1'b1;        // master samples MISO on the rising edge
                in[k] = miso;
                #(HALF_NS) sclk = 1'b0;
            end
        end
    endtask

    initial begin
        if (!$value$plusargs("tx=%s", tx_path) || !$value$plusargs("exp=%s", exp_path) ||
            !$value$plusargs("len=%s", len_path) || !$value$plusargs("frames=%d", n_frames) ||
            !$value$plusargs("bytes=%d", n_bytes)) begin
            $display("FAIL missing plusargs");
            $fatal(1);
        end
        $readmemh(tx_path, tx, 0, n_bytes - 1);
        $readmemh(exp_path, exp, 0, n_bytes - 1);
        $readmemh(len_path, len, 0, n_frames - 1);
        errors = 0;
        idx = 0;
        #1000;
        if (miso !== 1'bz) begin
            $display("FAIL MISO driven while chip select is high: %b", miso);
            $fatal(1);
        end
        for (f = 0; f < n_frames; f = f + 1) begin
            cs_n = 1'b0;
            #(4 * HALF_NS);                    // CE0 to first SCLK edge
            for (i = 0; i < len[f]; i = i + 1) begin
                xfer_byte(tx[idx], rx);
                if (rx !== exp[idx]) begin
                    if (errors == 0)
                        $display("FAIL frame=%0d byte=%0d sent=%h expected=%h got=%h", f, i, tx[idx], exp[idx], rx);
                    errors = errors + 1;
                end
                idx = idx + 1;
            end
            #(2 * HALF_NS) cs_n = 1'b1;
            #(8 * HALF_NS);
        end
        if (errors != 0) begin
            $display("FAIL errors=%0d of %0d bytes", errors, n_bytes);
            $fatal(1);
        end
        $display("PASS %0d/%0d frames=%0d", n_bytes, n_bytes, n_frames);
        $finish;
    end
endmodule

`default_nettype wire
