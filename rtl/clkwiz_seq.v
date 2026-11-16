`timescale 1ns / 1ps
`default_nettype none

// Clocking Wizard v6.0 reconfiguration over AXI4-Lite (ADR-023, PG065 "Dynamic Reconfiguration
// through AXI4-Lite").  On start: write 0x200 (DIVCLK, CLKFBOUT_MULT and FRAC) and 0x208
// (CLKOUT0_DIVIDE and FRAC) from the generated level table, wait until SR (0x04) bit 0 reads 1,
// write 0x25C = 0x3 (LOAD with the register settings), wait a while, then wait until SR bit 0 and
// the synchronised LOCKED are both 1.  busy is high from start until then.
// Plain RTL: the AMD IP itself is only instantiated in rtl/platform/xilinx/clk_gen_xilinx.v.
module clkwiz_seq (
    input  wire        clk,
    input  wire        rst,
    input  wire        start,
    input  wire [3:0]  level,
    output wire        busy,
    input  wire        locked,      // already synchronised to clk
    output reg  [10:0] m_awaddr,
    output reg         m_awvalid,
    input  wire        m_awready,
    output reg  [31:0] m_wdata,
    output wire [3:0]  m_wstrb,
    output reg         m_wvalid,
    input  wire        m_wready,
    input  wire        m_bvalid,
    output reg         m_bready,
    output wire [10:0] m_araddr,
    output reg         m_arvalid,
    input  wire        m_arready,
    input  wire [31:0] m_rdata,
    input  wire        m_rvalid,
    output reg         m_rready
);
`include "mmcm_turbo_table.vh"

    localparam [3:0] S_IDLE = 4'd0, S_W0 = 4'd1, S_W2 = 4'd2, S_POLL1 = 4'd3, S_LOAD = 4'd4,
                     S_SETTLE = 4'd5, S_POLL2 = 4'd6, S_WRITE = 4'd7, S_BRESP = 4'd8,
                     S_READ = 4'd9, S_RRESP = 4'd10, S_GAP = 4'd11;

    reg [3:0]  state, ret;          // ret: where a write or read returns to
    reg [3:0]  lv;
    reg [7:0]  timer;
    reg        aw_done, w_done;
    reg        sr_locked;

    assign busy     = (state != S_IDLE);
    assign m_wstrb  = 4'hF;
    assign m_araddr = 11'h004;

    always @(posedge clk) begin
        if (rst) begin
            state     <= S_IDLE;
            ret       <= S_IDLE;
            lv        <= 4'd0;
            timer     <= 8'd0;
            aw_done   <= 1'b0;
            w_done    <= 1'b0;
            sr_locked <= 1'b0;
            m_awaddr  <= 11'd0;
            m_awvalid <= 1'b0;
            m_wdata   <= 32'd0;
            m_wvalid  <= 1'b0;
            m_bready  <= 1'b0;
            m_arvalid <= 1'b0;
            m_rready  <= 1'b0;
        end else begin
            case (state)
                S_IDLE: if (start) begin
                    lv    <= level;
                    state <= S_W0;
                end
                // ---- the steps of PG065 -----------------------------------------------------
                S_W0: begin
                    m_awaddr <= 11'h200; m_wdata <= snt_clkwiz_reg0(lv);
                    m_awvalid <= 1'b1; m_wvalid <= 1'b1; aw_done <= 1'b0; w_done <= 1'b0;
                    ret <= S_W2; state <= S_WRITE;
                end
                S_W2: begin
                    m_awaddr <= 11'h208; m_wdata <= snt_clkwiz_reg2(lv);
                    m_awvalid <= 1'b1; m_wvalid <= 1'b1; aw_done <= 1'b0; w_done <= 1'b0;
                    ret <= S_POLL1; state <= S_WRITE;
                end
                S_POLL1: if (sr_locked) begin
                    sr_locked <= 1'b0;
                    state     <= S_LOAD;
                end else begin
                    m_arvalid <= 1'b1; ret <= S_POLL1; state <= S_READ;
                end
                S_LOAD: begin
                    m_awaddr <= 11'h25C; m_wdata <= 32'h0000_0003;
                    m_awvalid <= 1'b1; m_wvalid <= 1'b1; aw_done <= 1'b0; w_done <= 1'b0;
                    timer <= 8'd0;
                    ret <= S_SETTLE; state <= S_WRITE;
                end
                // Give the wizard time to drop LOCKED before waiting for it again.
                S_SETTLE: begin
                    timer <= timer + 1'b1;
                    if (&timer) state <= S_POLL2;
                end
                S_POLL2: if (sr_locked && locked) begin
                    sr_locked <= 1'b0;
                    state     <= S_IDLE;
                end else begin
                    m_arvalid <= 1'b1; ret <= S_POLL2; state <= S_READ;
                end
                // ---- AXI4-Lite write: address and data, then the response ------------------
                S_WRITE: begin
                    if (m_awvalid && m_awready) begin m_awvalid <= 1'b0; aw_done <= 1'b1; end
                    if (m_wvalid && m_wready)   begin m_wvalid  <= 1'b0; w_done  <= 1'b1; end
                    if ((aw_done || (m_awvalid && m_awready)) && (w_done || (m_wvalid && m_wready))) begin
                        m_bready <= 1'b1;
                        state    <= S_BRESP;
                    end
                end
                S_BRESP: if (m_bvalid) begin
                    m_bready <= 1'b0;
                    state    <= ret;
                end
                // ---- AXI4-Lite read of SR ----------------------------------------------------
                S_READ: if (m_arready) begin
                    m_arvalid <= 1'b0;
                    m_rready  <= 1'b1;
                    state     <= S_RRESP;
                end
                S_RRESP: if (m_rvalid) begin
                    m_rready  <= 1'b0;
                    sr_locked <= m_rdata[0];
                    timer     <= 8'd240;     // short gap before the next poll
                    state     <= m_rdata[0] ? ret : S_GAP;
                end
                S_GAP: begin
                    timer <= timer + 1'b1;
                    if (&timer) state <= ret;
                end
                default: state <= S_IDLE;
            endcase
        end
    end

    wire unused_rdata = &{1'b0, m_rdata[31:1]};
endmodule

`default_nettype wire
