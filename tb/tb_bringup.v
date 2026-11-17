`timescale 1ns / 1ps
`default_nettype none

// Bring-up designs without the Raspberry Pi (fpga/bringup/, ADR-026).
//   blink_top:      LED1 toggles every HALF clocks, LED2 is its inverse.
//   vcco_probe_top: PMOD1 pins 1-4 high, 7-10 low, WS2812B data line (N1, also J7) high, LEDs blink.
//   io_test_top:    LED1 = SW1 (PSW), LED2 = SW3 (DIP); the WS2812B colour shows START (R), STOP (G), RUN (B)
//                   as raw levels, because the button polarity is not documented.
module tb_bringup;
    localparam HALF = 40;                   // short divider for simulation
    localparam T0H = 2, T1H = 4, BITC = 6, RST = 30, REFRESH_LOG2 = 9;
    reg clk = 1'b0;
    always #25 clk = ~clk;                  // 20 MHz

    // ---- blink ------------------------------------------------------------------------------------
    wire b_led1, b_led2;
    blink_top #(.HALF(HALF)) u_blink (.clk_in(clk), .led1(b_led1), .led2(b_led2));

    // ---- VCCO probe ---------------------------------------------------------------------------------
    wire [3:0] p_hi, p_lo;
    wire p_ws, p_led1, p_led2;
    vcco_probe_top #(.HALF(HALF)) u_probe (.clk_in(clk), .pmod1_hi(p_hi), .pmod1_lo(p_lo), .ws2812_dout(p_ws),
                                           .led1(p_led1), .led2(p_led2));

    // ---- I/O test -------------------------------------------------------------------------------------
    reg start = 1'b0, stop = 1'b0, run = 1'b0, psw = 1'b0, dip = 1'b0;
    wire t_led1, t_led2, t_ws;
    io_test_top #(.T0H_CYC(T0H), .T1H_CYC(T1H), .BIT_CYC(BITC), .RESET_CYC(RST), .REFRESH_LOG2(REFRESH_LOG2)) u_io (
        .clk_in(clk), .btn_start(start), .btn_stop(stop), .btn_run(run), .btn_psw(psw), .dip_sw(dip),
        .led1(t_led1), .led2(t_led2), .ws2812_dout(t_ws));

    // WS2812B receiver: a bit is 1 when its high time is T1H clocks.
    reg [23:0] rx_word = 24'd0, rx_last = 24'd0;
    integer rx_bits = 0, hi = 0, frames = 0, gap = 0;
    reg prev_ws = 1'b0;
    always @(posedge clk) begin
        if (t_ws) begin hi = hi + 1; gap = 0; end else gap = gap + 1;
        if (prev_ws && !t_ws) begin
            rx_word = {rx_word[22:0], (hi >= T1H)};
            rx_bits = rx_bits + 1; hi = 0;
            if (rx_bits == 24) begin rx_last = rx_word; rx_bits = 0; frames = frames + 1; end
        end
        if (gap > RST / 2) rx_bits = 0;
        prev_ws = t_ws;
    end

    integer checks = 0, passed = 0, toggles = 0, last_toggle = 0, cyc = 0, bad_period = 0;
    reg prev_led = 1'b0;
    always @(posedge clk) begin
        cyc = cyc + 1;
        if (b_led1 !== prev_led) begin
            if (toggles > 0 && cyc - last_toggle != HALF) bad_period = bad_period + 1;
            toggles = toggles + 1; last_toggle = cyc;
        end
        prev_led = b_led1;
    end

    task check(input cond, input [8*40-1:0] what);
        begin checks = checks + 1; if (cond) passed = passed + 1; else $display("FAIL %0s", what); end
    endtask

    task expect_colour(input [23:0] grb, input [8*40-1:0] what);
        integer f0;
        begin
            f0 = frames;
            wait (frames >= f0 + 2);          // a full frame sent after the inputs changed
            check(rx_last === grb, what);
            if (rx_last !== grb) $display("     got %h expected %h", rx_last, grb);
        end
    endtask

    initial begin
        repeat (10 * HALF) @(posedge clk);
        check(toggles >= 9 && bad_period == 0, "blink period is not HALF clocks");
        check(b_led2 === ~b_led1, "blink LED2 is not the inverse of LED1");
        check(p_hi === 4'hF && p_lo === 4'h0 && p_ws === 1'b1, "probe levels");
        check(p_led2 === ~p_led1, "probe LEDs do not alternate");
        expect_colour(24'h00_00_00, "io colour with all inputs low");
        start = 1'b1; expect_colour(24'h00_20_00, "START shows red");
        start = 1'b0; stop = 1'b1; expect_colour(24'h20_00_00, "STOP shows green");
        stop = 1'b0; run = 1'b1; expect_colour(24'h00_00_20, "RUN shows blue");
        run = 1'b0; psw = 1'b1; dip = 1'b0; repeat (5) @(posedge clk);
        check(t_led1 === 1'b1 && t_led2 === 1'b0, "PSW on LED1");
        psw = 1'b0; dip = 1'b1; repeat (5) @(posedge clk);
        check(t_led1 === 1'b0 && t_led2 === 1'b1, "DIP on LED2");
        if (passed == checks) $display("PASS %0d/%0d", passed, checks);
        else begin $display("FAIL %0d/%0d", passed, checks); $fatal(1); end
        $finish;
    end
endmodule

`default_nettype wire
