`timescale 1ns / 1ps
`default_nettype none

// M18 (ADR-018, ADR-023): xadc_temp polls DRP address 00h and keeps the 12 MSBs as the temperature code.
// Uses the behavioural XADC model of rtl/platform/sim/xadc_prim_sim.v.
module tb_xadc_temp;
    localparam [11:0] CODE = 12'd2423;   // about 25 C by UG480 Equation 2-6
    reg clk = 1'b0;
    reg rst = 1'b1;
    always #4 clk = ~clk;

    wire [11:0] code;
    wire        valid;
    xadc_temp #(.POLL_LOG2(6), .SIM_CODE(CODE)) dut (.clk(clk), .rst(rst), .code(code), .valid(valid));

    integer reads = 0, bad_addr = 0, checks = 0, passed = 0;
    always @(posedge clk) if (dut.den) begin
        reads = reads + 1;
        if (dut.daddr !== 7'h00) bad_addr = bad_addr + 1;
    end

    initial begin
        repeat (5) @(posedge clk);
        rst <= 1'b0;
        // Not valid before the first read completes.
        @(posedge clk);
        checks = checks + 1; if (valid === 1'b0) passed = passed + 1;
        else $display("FAIL valid set before the first DRP read");
        repeat (400) @(posedge clk);
        checks = checks + 1; if (valid === 1'b1 && code === CODE) passed = passed + 1;
        else $display("FAIL expected code %0d valid 1, got %0d valid %b", CODE, code, valid);
        checks = checks + 1; if (reads >= 4 && bad_addr == 0) passed = passed + 1;
        else $display("FAIL reads=%0d with %0d at a DRP address other than 00h", reads, bad_addr);
        // Reset clears valid.
        rst <= 1'b1; @(posedge clk); @(posedge clk);
        checks = checks + 1; if (valid === 1'b0) passed = passed + 1;
        else $display("FAIL valid survives reset");
        if (passed == checks) $display("PASS %0d/%0d reads=%0d", passed, checks, reads);
        else begin $display("FAIL %0d/%0d", passed, checks); $fatal(1); end
        $finish;
    end
endmodule

`default_nettype wire
