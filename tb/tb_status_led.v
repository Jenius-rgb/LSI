`timescale 1ns / 1ps
`default_nettype none

// M17 (ADR-017): status_led maps {fatal, turbo, done, busy} to one WS2812B colour and sends a frame
// whenever the colour changes and every 2^REFRESH_LOG2 clocks.
module tb_status_led;
    reg clk = 1'b0, rst = 1'b1;
    reg fatal = 1'b0, turbo = 1'b0, done = 1'b0, busy = 1'b0;
    always #4 clk = ~clk;
    wire dout;
    status_led #(.CLK_HZ(10_000_000), .REFRESH_LOG2(12)) dut (
        .clk(clk), .rst(rst), .fatal(fatal), .is_turbo(turbo), .done(done), .busy(busy), .dout(dout));

    integer checks = 0, passed = 0, frames = 0;
    always @(posedge clk) if (dut.tx_start) frames = frames + 1;

    task expect_colour(input [23:0] grb, input [8*24-1:0] what);
        begin
            repeat (2) @(posedge clk);
            checks = checks + 1;
            if (dut.colour === grb) passed = passed + 1;
            else $display("FAIL %0s: colour %h, expected %h", what, dut.colour, grb);
        end
    endtask

    integer frames0;
    initial begin
        repeat (3) @(posedge clk); rst <= 1'b0;
        expect_colour(24'h04_04_04, "idle");
        busy = 1'b1;                expect_colour(24'h00_00_20, "busy");
        turbo = 1'b1;               expect_colour(24'h00_20_20, "busy in turbo");
        busy = 1'b0; turbo = 1'b0; done = 1'b1; expect_colour(24'h20_00_00, "done");
        fatal = 1'b1;               expect_colour(24'h00_20_00, "fatal");
        // A colour change starts a frame once the transmitter is free.
        frames0 = frames;
        fatal = 1'b0;
        repeat (20000) @(posedge clk);
        checks = checks + 1;
        if (frames > frames0) passed = passed + 1; else $display("FAIL no frame after a colour change");
        // Periodic refresh without a change.
        frames0 = frames;
        repeat (20000) @(posedge clk);
        checks = checks + 1;
        if (frames > frames0) passed = passed + 1; else $display("FAIL no refresh frame");
        if (passed == checks) $display("PASS %0d/%0d frames=%0d", passed, checks, frames);
        else begin $display("FAIL %0d/%0d", passed, checks); $fatal(1); end
        $finish;
    end
endmodule

`default_nettype wire
