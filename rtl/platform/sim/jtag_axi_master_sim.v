`timescale 1ns / 1ps
`default_nettype none

// Simulation model of the JTAG-to-AXI master (ADR-025): replays a transaction log written by
// sentinel.transport_jtag.RecordingAxi and compares every read with the value the Python device model
// returned (bits under the mask).  Log entries are four 32-bit words:
//   {op, 20'd0, strb}, address, data or expected data, compare mask
//   op 0x10 write, 0x11 read, 0x12 poll (read until (data & mask) == expected), 0xFF end.
// Prints PASS n/n or FAIL with the first mismatch, then finishes the simulation.
module jtag_axi_master_sim #(
    parameter MAX_LOG = 400000
) (
    input  wire        clk,
    input  wire        rst,
    output reg  [31:0] m_awaddr,
    output reg         m_awvalid,
    input  wire        m_awready,
    output reg  [31:0] m_wdata,
    output reg  [3:0]  m_wstrb,
    output reg         m_wvalid,
    input  wire        m_wready,
    input  wire [1:0]  m_bresp,
    input  wire        m_bvalid,
    output reg         m_bready,
    output reg  [31:0] m_araddr,
    output reg         m_arvalid,
    input  wire        m_arready,
    input  wire [31:0] m_rdata,
    input  wire [1:0]  m_rresp,
    input  wire        m_rvalid,
    output reg         m_rready
);
    reg [31:0] log [0:MAX_LOG-1];
    reg [8*200-1:0] path;
    integer pc, checks, errors, polls;
    reg [31:0] got;
    reg        done_poll;

    task axi_write(input [31:0] addr, input [31:0] data, input [3:0] strb);
        begin
            @(posedge clk);
            m_awaddr <= addr; m_wdata <= data; m_wstrb <= strb; m_awvalid <= 1'b1; m_wvalid <= 1'b1;
            @(posedge clk);
            while (!(m_awready === 1'b1 && m_wready === 1'b1)) @(posedge clk);
            m_awvalid <= 1'b0; m_wvalid <= 1'b0; m_bready <= 1'b1;
            @(posedge clk);
            while (m_bvalid !== 1'b1) @(posedge clk);
            m_bready <= 1'b0;
        end
    endtask

    task axi_read(input [31:0] addr, output [31:0] data);
        begin
            @(posedge clk);
            m_araddr <= addr; m_arvalid <= 1'b1;
            @(posedge clk);
            while (m_arready !== 1'b1) @(posedge clk);
            m_arvalid <= 1'b0; m_rready <= 1'b1;
            @(posedge clk);
            while (m_rvalid !== 1'b1) @(posedge clk);
            data = m_rdata;
            m_rready <= 1'b0;
        end
    endtask

    initial begin
        m_awaddr = 0; m_awvalid = 0; m_wdata = 0; m_wstrb = 0; m_wvalid = 0; m_bready = 0;
        m_araddr = 0; m_arvalid = 0; m_rready = 0;
        if (!$value$plusargs("log=%s", path)) begin $display("FAIL no log"); $fatal(1); end
        $readmemh(path, log);
        checks = 0; errors = 0; polls = 0;
        wait (rst === 1'b1);
        wait (rst === 1'b0);
        repeat (20) @(posedge clk);
        pc = 0;
        while (log[pc][31:24] !== 8'hFF) begin
            case (log[pc][31:24])
                8'h10: axi_write(log[pc + 1], log[pc + 2], log[pc][3:0]);
                8'h11: begin
                    axi_read(log[pc + 1], got);
                    if (log[pc + 3] != 32'd0) begin
                        checks = checks + 1;
                        if ((got & log[pc + 3]) !== (log[pc + 2] & log[pc + 3])) begin
                            if (errors == 0)
                                $display("FAIL log_entry=%0d addr=%h expected=%h got=%h mask=%h", pc / 4, log[pc + 1], log[pc + 2], got, log[pc + 3]);
                            errors = errors + 1;
                        end
                    end
                end
                8'h12: begin
                    done_poll = 1'b0;
                    while (!done_poll) begin
                        axi_read(log[pc + 1], got);
                        polls = polls + 1;
                        if ((got & log[pc + 3]) == log[pc + 2]) done_poll = 1'b1;
                        if (polls > 2000000) begin $display("FAIL poll timeout"); $fatal(1); end
                    end
                end
                default: begin $display("FAIL bad log op %h at %0d", log[pc][31:24], pc / 4); $fatal(1); end
            endcase
            pc = pc + 4;
        end
        if (errors == 0 && checks > 0) $display("PASS %0d/%0d polls=%0d", checks, checks, polls);
        else begin $display("FAIL %0d errors in %0d checks", errors, checks); $fatal(1); end
        $finish;
    end

    wire unused_resp = &{1'b0, m_bresp, m_rresp};
endmodule

`default_nettype wire
