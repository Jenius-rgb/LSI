`timescale 1ns / 1ps

// Unit test of the SPI slave against a byte-addressed memory model, at the guaranteed
// limit f_SCLK = f_clk / 8.
module tb_spi_slave;
    reg clk = 0;
    reg rst = 1;
    always #5 clk = ~clk;       // 100 MHz

    reg sclk = 0, cs_n = 1, mosi = 0;
    wire miso;
    wire bus_wr, bus_rd;
    wire [23:0] bus_addr;
    wire [7:0] bus_wdata;
    reg  [7:0] mem [0:255];
    reg  [7:0] bus_rdata = 0;
    reg        bus_rvalid = 0;
    reg  [1:0] rd_delay = 0;

    spi_slave dut (
        .clk(clk), .rst(rst), .sclk(sclk), .cs_n(cs_n), .mosi(mosi), .miso(miso),
        .id_word(64'h534E544C_00_01_08_05),
        .bus_wr(bus_wr), .bus_rd(bus_rd), .bus_addr(bus_addr), .bus_wdata(bus_wdata),
        .bus_rdata(bus_rdata), .bus_rvalid(bus_rvalid));

    // Memory with 2-cycle read latency.
    always @(posedge clk) begin
        bus_rvalid <= 0;
        if (bus_wr) mem[bus_addr[7:0]] <= bus_wdata;
        if (bus_rd) rd_delay <= 2;
        else if (rd_delay != 0) begin
            rd_delay <= rd_delay - 1;
            if (rd_delay == 1) begin
                bus_rdata <= mem[bus_addr[7:0]];
                bus_rvalid <= 1;
            end
        end
    end

    integer errors = 0, checks = 0;
    reg [7:0] rx;

    task xfer;       // SCLK = clk / 8: four clk per half period
        input  [7:0] tx;
        output [7:0] got;
        integer b;
        begin
            for (b = 7; b >= 0; b = b - 1) begin
                mosi = tx[b];
                repeat (4) @(posedge clk);
                sclk = 1;
                got[b] = miso;
                repeat (4) @(posedge clk);
                sclk = 0;
            end
        end
    endtask

    task check;
        input [7:0] got;
        input [7:0] want;
        begin
            checks = checks + 1;
            if (got !== want) begin
                if (errors == 0) $display("FAIL byte=%0d expected=%h got=%h", checks, want, got);
                errors = errors + 1;
            end
        end
    endtask

    integer i;
    initial begin
        repeat (6) @(posedge clk);
        rst = 0;
        repeat (6) @(posedge clk);

        // WRITE ten bytes at 0x000040.
        cs_n = 0;
        repeat (4) @(posedge clk);
        xfer(8'h02, rx); xfer(8'h00, rx); xfer(8'h00, rx); xfer(8'h40, rx);
        for (i = 0; i < 10; i = i + 1) xfer(8'hA0 + i, rx);
        repeat (4) @(posedge clk);
        cs_n = 1;
        repeat (20) @(posedge clk);

        // READ them back.
        cs_n = 0;
        repeat (4) @(posedge clk);
        xfer(8'h03, rx); xfer(8'h00, rx); xfer(8'h00, rx); xfer(8'h40, rx);
        xfer(8'h00, rx);  // dummy
        for (i = 0; i < 10; i = i + 1) begin
            xfer(8'h00, rx);
            check(rx, 8'hA0 + i);
        end
        repeat (4) @(posedge clk);
        cs_n = 1;
        repeat (20) @(posedge clk);

        // ID.
        cs_n = 0;
        repeat (4) @(posedge clk);
        xfer(8'h9F, rx);
        xfer(8'h00, rx); check(rx, 8'h53);
        xfer(8'h00, rx); check(rx, 8'h4E);
        xfer(8'h00, rx); check(rx, 8'h54);
        xfer(8'h00, rx); check(rx, 8'h4C);
        xfer(8'h00, rx); check(rx, 8'h00);
        xfer(8'h00, rx); check(rx, 8'h01);
        xfer(8'h00, rx); check(rx, 8'h08);
        xfer(8'h00, rx); check(rx, 8'h05);
        repeat (4) @(posedge clk);
        cs_n = 1;
        repeat (20) @(posedge clk);

        // Single-byte read straight after a new CS assertion.
        cs_n = 0;
        repeat (4) @(posedge clk);
        xfer(8'h03, rx); xfer(8'h00, rx); xfer(8'h00, rx); xfer(8'h45, rx);
        xfer(8'h00, rx);
        xfer(8'h00, rx); check(rx, 8'hA5);
        repeat (4) @(posedge clk);
        cs_n = 1;
        repeat (20) @(posedge clk);

        if (errors != 0) begin
            $display("FAIL errors=%0d of %0d", errors, checks);
            $fatal(1);
        end
        $display("PASS %0d/%0d", checks, checks);
        $finish;
    end
endmodule
