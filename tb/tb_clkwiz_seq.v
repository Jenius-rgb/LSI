`timescale 1ns / 1ps
`default_nettype none

// ADR-023: clkwiz_seq programs a Clocking Wizard v6.0 over AXI4-Lite in the order of PG065
// ("Dynamic Reconfiguration through AXI4-Lite"): 0x200, 0x208, wait for SR (0x04) bit 0, write
// 0x25C = 0x3, wait for lock.  The slave below is a behavioural model of that register interface,
// not the AMD IP.  Expected register words come from tools/gen_mmcm_table.py (+exp file).
module tb_clkwiz_seq;
    localparam LOCK_CYC = 300;
    reg clk = 1'b0, rst = 1'b1;
    always #4 clk = ~clk;

    reg        start = 1'b0;
    reg  [3:0] level = 4'd0;
    wire       busy;
    wire [10:0] awaddr, araddr;
    wire        awvalid, wvalid, bready, arvalid, rready;
    wire [31:0] wdata;
    wire [3:0]  wstrb;
    reg         awready = 1'b0, wready = 1'b0, bvalid = 1'b0, arready = 1'b0, rvalid = 1'b0;
    reg  [31:0] rdata = 32'd0;
    reg         locked = 1'b0;

    clkwiz_seq dut (
        .clk(clk), .rst(rst), .start(start), .level(level), .busy(busy), .locked(locked),
        .m_awaddr(awaddr), .m_awvalid(awvalid), .m_awready(awready), .m_wdata(wdata), .m_wstrb(wstrb),
        .m_wvalid(wvalid), .m_wready(wready), .m_bvalid(bvalid), .m_bready(bready),
        .m_araddr(araddr), .m_arvalid(arvalid), .m_arready(arready), .m_rdata(rdata), .m_rvalid(rvalid), .m_rready(rready));

    // ---- behavioural register model (PG065 Table 2-2) ---------------------------------------
    reg [31:0] reg0 = 32'h0000_3201, reg2 = 32'h0000_0008, applied0 = 0, applied2 = 0;
    integer    lock_timer = 20, loads = 0, protocol_errors = 0;
    always @(posedge clk) begin
        awready <= 1'b0; wready <= 1'b0; arready <= 1'b0;
        if (bvalid && bready) bvalid <= 1'b0;
        if (rvalid && rready) rvalid <= 1'b0;
        if (awvalid && wvalid && !awready && !bvalid) begin
            awready <= 1'b1; wready <= 1'b1; bvalid <= 1'b1;
            if (wstrb !== 4'hF) protocol_errors = protocol_errors + 1;
            case (awaddr)
                11'h200: reg0 <= wdata;
                11'h208: reg2 <= wdata;
                11'h25C: if (wdata[0]) begin
                    if (!locked) begin protocol_errors = protocol_errors + 1; $display("FAIL LOAD while not locked"); end
                    if (!wdata[1]) begin protocol_errors = protocol_errors + 1; $display("FAIL LOAD without SADDR"); end
                    applied0 <= reg0; applied2 <= reg2; loads = loads + 1;
                    locked <= 1'b0; lock_timer = LOCK_CYC;
                end
                default: begin protocol_errors = protocol_errors + 1; $display("FAIL write to %h", awaddr); end
            endcase
        end
        if (arvalid && !arready && !rvalid) begin
            arready <= 1'b1; rvalid <= 1'b1;
            rdata <= (araddr == 11'h004) ? {31'd0, locked} : 32'd0;
            if (araddr != 11'h004) protocol_errors = protocol_errors + 1;
        end
        if (lock_timer > 0) begin
            lock_timer = lock_timer - 1;
            if (lock_timer == 0) locked <= 1'b1;
        end
    end

    // ---- stimulus ----------------------------------------------------------------------------
    reg [31:0] expected [0:31];
    reg [8*256-1:0] path;
    integer i, lv, checks = 0, passed = 0, loads0;
    integer order [0:15];
    initial begin
        if (!$value$plusargs("exp=%s", path)) begin $display("FAIL no exp"); $fatal(1); end
        $readmemh(path, expected);
        order[0] = 3; order[1] = 0; order[2] = 15; order[3] = 7; order[4] = 1; order[5] = 12; order[6] = 9; order[7] = 4;
        order[8] = 14; order[9] = 2; order[10] = 11; order[11] = 6; order[12] = 13; order[13] = 8; order[14] = 5; order[15] = 10;
        repeat (3) @(posedge clk); rst <= 1'b0;
        // Start right after reset, before the model has locked: the sequencer must wait for SR.
        for (i = 0; i < 16; i = i + 1) begin
            lv = order[i];
            loads0 = loads;
            @(posedge clk); level <= lv[3:0]; start <= 1'b1;
            @(posedge clk); start <= 1'b0;
            wait (busy === 1'b1);
            wait (busy === 1'b0);
            checks = checks + 3;
            if (applied0 === expected[2 * lv] && applied2 === expected[2 * lv + 1]) passed = passed + 1;
            else $display("FAIL level %0d: applied %h %h, expected %h %h", lv, applied0, applied2, expected[2 * lv], expected[2 * lv + 1]);
            if (locked === 1'b1) passed = passed + 1; else $display("FAIL level %0d: busy fell before lock", lv);
            if (loads == loads0 + 1) passed = passed + 1; else $display("FAIL level %0d: %0d loads", lv, loads - loads0);
        end
        checks = checks + 1;
        if (protocol_errors == 0) passed = passed + 1; else $display("FAIL %0d protocol errors", protocol_errors);
        if (passed == checks) $display("PASS %0d/%0d", passed, checks);
        else begin $display("FAIL %0d/%0d", passed, checks); $fatal(1); end
        $finish;
    end
endmodule

`default_nettype wire
