`timescale 1ns / 1ps
`default_nettype none

// M17 (ADR-017): ws2812_tx sends 24 bits MSB first; a 1 is a long high pulse, a 0 a short one,
// every bit lasts BIT_CYC clocks, and the line stays low for at least RESET_CYC after the frame.
module tb_ws2812_tx;
    localparam T0H = 5, T1H = 10, BITC = 16, RST = 60;
    localparam [23:0] WORD = 24'hA5_3C_81;
    reg clk = 1'b0, rst = 1'b1, start = 1'b0;
    always #4 clk = ~clk;
    wire dout, busy;
    ws2812_tx #(.T0H_CYC(T0H), .T1H_CYC(T1H), .BIT_CYC(BITC), .RESET_CYC(RST)) dut (
        .clk(clk), .rst(rst), .start(start), .grb(WORD), .dout(dout), .busy(busy));

    integer high = 0, low = 0, nbit = 0, errors = 0, checks = 0, last_low = 0;
    reg prev = 1'b0;
    always @(posedge clk) begin
        if (dout) high = high + 1; else low = low + 1;
        if (prev && !dout) begin                // falling edge: one bit's high time is known
            checks = checks + 1;
            if (high != (WORD[23 - nbit] ? T1H : T0H)) begin
                errors = errors + 1;
                $display("FAIL bit %0d high for %0d clocks", nbit, high);
            end
            nbit = nbit + 1; high = 0; low = 0;
        end
        if (!prev && dout && nbit > 0) begin    // rising edge: previous bit length = high + low
            checks = checks + 1;
            if (last_low + ((WORD[24 - nbit] ? T1H : T0H)) != BITC) begin
                errors = errors + 1;
                $display("FAIL bit %0d lasts %0d clocks", nbit - 1, last_low + (WORD[24 - nbit] ? T1H : T0H));
            end
        end
        if (!dout) last_low = low + 1;
        prev = dout;
    end

    integer quiet = 0;
    initial begin
        repeat (3) @(posedge clk); rst <= 1'b0;
        @(posedge clk); start <= 1'b1; @(posedge clk); start <= 1'b0;
        wait (busy === 1'b1);
        wait (busy === 1'b0);
        quiet = low;
        checks = checks + 2;
        if (nbit != 24) begin errors = errors + 1; $display("FAIL %0d bits sent", nbit); end
        if (quiet < RST) begin errors = errors + 1; $display("FAIL reset low time %0d < %0d", quiet, RST); end
        if (errors == 0) $display("PASS %0d/%0d", checks, checks);
        else begin $display("FAIL %0d errors in %0d checks", errors, checks); $fatal(1); end
        $finish;
    end
endmodule

`default_nettype wire
