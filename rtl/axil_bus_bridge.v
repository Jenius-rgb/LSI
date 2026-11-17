`timescale 1ns / 1ps
`default_nettype none

// AXI4-Lite slave to the SENTINEL host byte bus (ADR-025).  32-bit data, little-endian: byte lane i
// of a word at address A is bus address A + i.  A write issues one bus write per enabled strobe; a
// read issues four bus reads and waits for bus_rvalid after each.  Addresses 0xFFFFF8 and 0xFFFFFC
// return the two halves of the ID word (the same word as SPI command 0x9F) without a bus access.
// Responses are always OKAY.  One transaction at a time.
module axil_bus_bridge (
    input  wire        clk,
    input  wire        rst,
    input  wire [31:0] s_awaddr,
    input  wire        s_awvalid,
    output reg         s_awready,
    input  wire [31:0] s_wdata,
    input  wire [3:0]  s_wstrb,
    input  wire        s_wvalid,
    output reg         s_wready,
    output wire [1:0]  s_bresp,
    output reg         s_bvalid,
    input  wire        s_bready,
    input  wire [31:0] s_araddr,
    input  wire        s_arvalid,
    output reg         s_arready,
    output reg  [31:0] s_rdata,
    output wire [1:0]  s_rresp,
    output reg         s_rvalid,
    input  wire        s_rready,
    output reg         bus_wr,
    output reg         bus_rd,
    output reg  [23:0] bus_addr,
    output reg  [7:0]  bus_wdata,
    input  wire [7:0]  bus_rdata,
    input  wire        bus_rvalid,
    input  wire [63:0] id_word
);
    localparam [2:0] S_IDLE = 3'd0, S_WBYTE = 3'd1, S_BRESP = 3'd2, S_RBYTE = 3'd3, S_RWAIT = 3'd4, S_RRESP = 3'd5;
    reg [2:0]  state;
    reg [21:0] word_addr;      // address bits [23:2]
    reg [31:0] wdata;
    reg [3:0]  wstrb;
    reg [1:0]  lane;

    // The bus is 24-bit and word aligned; the other address bits are ignored.
    wire unused_addr = &{1'b0, s_awaddr[31:24], s_awaddr[1:0], s_araddr[31:24], s_araddr[1:0]};

    assign s_bresp = 2'b00;
    assign s_rresp = 2'b00;

    always @(posedge clk) begin
        bus_wr    <= 1'b0;
        bus_rd    <= 1'b0;
        s_awready <= 1'b0;
        s_wready  <= 1'b0;
        s_arready <= 1'b0;
        if (rst) begin
            state    <= S_IDLE;
            s_bvalid <= 1'b0;
            s_rvalid <= 1'b0;
            s_rdata  <= 32'd0;
            word_addr <= 22'd0;
            wdata    <= 32'd0;
            wstrb    <= 4'd0;
            lane     <= 2'd0;
            bus_addr <= 24'd0;
            bus_wdata <= 8'd0;
        end else begin
            case (state)
                S_IDLE: begin
                    if (s_awvalid && s_wvalid) begin
                        s_awready <= 1'b1;
                        s_wready  <= 1'b1;
                        word_addr <= s_awaddr[23:2];
                        wdata     <= s_wdata;
                        wstrb     <= s_wstrb;
                        lane      <= 2'd0;
                        state     <= S_WBYTE;
                    end else if (s_arvalid) begin
                        s_arready <= 1'b1;
                        word_addr <= s_araddr[23:2];
                        lane      <= 2'd0;
                        if (s_araddr[23:3] == 21'h1FFFFF) begin     // ID window
                            s_rdata  <= s_araddr[2] ? id_word[31:0] : id_word[63:32];
                            s_rvalid <= 1'b1;
                            state    <= S_RRESP;
                        end else begin
                            state <= S_RBYTE;
                        end
                    end
                end
                S_WBYTE: begin
                    if (wstrb[lane]) begin
                        bus_wr    <= 1'b1;
                        bus_addr  <= {word_addr, lane};
                        bus_wdata <= wdata[8 * lane +: 8];
                    end
                    lane <= lane + 1'b1;
                    if (lane == 2'd3) begin
                        s_bvalid <= 1'b1;
                        state    <= S_BRESP;
                    end
                end
                S_BRESP: if (s_bready) begin
                    s_bvalid <= 1'b0;
                    state    <= S_IDLE;
                end
                S_RBYTE: begin
                    bus_rd   <= 1'b1;
                    bus_addr <= {word_addr, lane};
                    state    <= S_RWAIT;
                end
                S_RWAIT: if (bus_rvalid) begin
                    s_rdata[8 * lane +: 8] <= bus_rdata;
                    lane <= lane + 1'b1;
                    if (lane == 2'd3) begin
                        s_rvalid <= 1'b1;
                        state    <= S_RRESP;
                    end else begin
                        state <= S_RBYTE;
                    end
                end
                S_RRESP: if (s_rready) begin
                    s_rvalid <= 1'b0;
                    state    <= S_IDLE;
                end
                default: state <= S_IDLE;
            endcase
        end
    end
endmodule

`default_nettype wire
