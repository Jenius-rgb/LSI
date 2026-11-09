`timescale 1ns / 1ps
`default_nettype none

// SPI slave (mode 0, MSB first, CS active low), oversampled by clk (SPEC 12.1).
// Guaranteed for f_SCLK <= f_clk / 8.  Commands (SPEC 12.2):
//   0x02 WRITE [A23:16][A15:8][A7:0][data...]
//   0x03 READ  [A23:16][A15:8][A7:0][dummy] then data out on MISO
//   0x9F ID    then 8 bytes out: id_word
// Addresses auto-increment.  Reads are issued one byte ahead, so bus reads may take a few
// clock cycles to return data (bus_rd pulses, data sampled on bus_rvalid).
module spi_slave (
    input  wire        clk,
    input  wire        rst,
    input  wire        sclk,
    input  wire        cs_n,
    input  wire        mosi,
    output reg         miso,
    input  wire [63:0] id_word,

    output reg         bus_wr,
    output reg         bus_rd,
    output reg  [23:0] bus_addr,
    output reg  [7:0]  bus_wdata,
    input  wire [7:0]  bus_rdata,
    input  wire        bus_rvalid
);
    localparam [7:0] CMD_WRITE = 8'h02, CMD_READ = 8'h03, CMD_ID = 8'h9F;
    localparam [1:0] P_CMD = 2'd0, P_ADDR = 2'd1, P_DATA = 2'd2, P_ID = 2'd3;

    reg sclk_s1, sclk_s2, sclk_d;
    reg cs_s1, cs_s2, cs_d;
    reg mosi_s1, mosi_s2;

    wire sclk_rise = sclk_s2 & ~sclk_d;
    wire sclk_fall = ~sclk_s2 & sclk_d;
    wire selected  = ~cs_s2;
    wire cs_fall   = ~cs_s2 & cs_d;

    reg [1:0]  phase;
    reg [7:0]  cmd;
    reg [2:0]  bit_cnt;
    reg [6:0]  rx_shift;
    reg [7:0]  tx_shift;
    reg [7:0]  tx_next;
    reg [1:0]  addr_bytes;
    reg [23:0] addr;
    reg        dummy_pending;
    reg [3:0]  id_byte;
    reg        tx_load;

    wire [7:0] rx_byte = {rx_shift, mosi_s2};
    wire       byte_done = sclk_rise & (bit_cnt == 3'd7);

    always @(posedge clk) begin
        sclk_s1 <= sclk;
        sclk_s2 <= sclk_s1;
        sclk_d  <= sclk_s2;
        cs_s1   <= cs_n;
        cs_s2   <= cs_s1;
        cs_d    <= cs_s2;
        mosi_s1 <= mosi;
        mosi_s2 <= mosi_s1;
    end

    always @(posedge clk) begin
        bus_wr <= 1'b0;
        bus_rd <= 1'b0;
        if (rst) begin
            miso          <= 1'b0;
            phase         <= P_CMD;
            bit_cnt       <= 3'd0;
            addr_bytes    <= 2'd0;
            dummy_pending <= 1'b0;
            id_byte       <= 4'd0;
            tx_load       <= 1'b0;
            cmd           <= 8'd0;
            tx_shift      <= 8'd0;
            tx_next       <= 8'd0;
            rx_shift      <= 7'd0;
            addr          <= 24'd0;
            bus_addr      <= 24'd0;
            bus_wdata     <= 8'd0;
        end else if (!selected) begin
            phase      <= P_CMD;
            bit_cnt    <= 3'd0;
            addr_bytes <= 2'd0;
            id_byte    <= 4'd0;
            tx_load    <= 1'b0;
            dummy_pending <= 1'b0;
        end else begin
            if (cs_fall) begin
                miso <= 1'b0;
            end

            if (bus_rvalid) tx_next <= bus_rdata;

            if (sclk_rise) begin
                rx_shift <= rx_byte[6:0];
                bit_cnt  <= bit_cnt + 1'b1;
            end

            if (byte_done) begin
                case (phase)
                    P_CMD: begin
                        cmd <= rx_byte;
                        addr_bytes <= 2'd0;
                        if (rx_byte == CMD_ID) begin
                            phase   <= P_ID;
                            id_byte <= 4'd1;
                            tx_next <= id_word[63:56];
                            tx_load <= 1'b1;
                        end else begin
                            phase <= P_ADDR;
                        end
                    end
                    P_ADDR: begin
                        addr <= {addr[15:0], rx_byte};
                        if (addr_bytes == 2'd2) begin
                            phase <= P_DATA;
                            if (cmd == CMD_READ) begin
                                dummy_pending <= 1'b1;
                                bus_addr <= {addr[15:0], rx_byte};
                                bus_rd   <= 1'b1;
                                addr     <= {addr[15:0], rx_byte} + 1'b1;
                            end
                        end
                        addr_bytes <= addr_bytes + 1'b1;
                    end
                    P_DATA: begin
                        if (cmd == CMD_WRITE) begin
                            bus_addr  <= addr;
                            bus_wdata <= rx_byte;
                            bus_wr    <= 1'b1;
                            addr      <= addr + 1'b1;
                        end else if (dummy_pending) begin
                            dummy_pending <= 1'b0;
                            tx_load <= 1'b1;
                        end else begin
                            tx_load <= 1'b1;
                        end
                    end
                    P_ID: begin
                        tx_load <= 1'b1;
                        if (id_byte < 4'd8) begin
                            case (id_byte)
                                4'd1: tx_next <= id_word[55:48];
                                4'd2: tx_next <= id_word[47:40];
                                4'd3: tx_next <= id_word[39:32];
                                4'd4: tx_next <= id_word[31:24];
                                4'd5: tx_next <= id_word[23:16];
                                4'd6: tx_next <= id_word[15:8];
                                default: tx_next <= id_word[7:0];
                            endcase
                            id_byte <= id_byte + 1'b1;
                        end else begin
                            tx_next <= 8'd0;
                        end
                    end
                    default: phase <= P_CMD;
                endcase
            end

            if (sclk_fall) begin
                if (tx_load) begin
                    // First falling edge after a byte boundary: start the next byte.
                    tx_load  <= 1'b0;
                    miso     <= tx_next[7];
                    tx_shift <= {tx_next[6:0], 1'b0};
                    if (phase == P_DATA && cmd == CMD_READ && !dummy_pending) begin
                        // The byte now leaving was fetched earlier; fetch the one after it.
                        bus_addr <= addr;
                        bus_rd   <= 1'b1;
                        addr     <= addr + 1'b1;
                    end
                end else begin
                    miso     <= tx_shift[7];
                    tx_shift <= {tx_shift[6:0], 1'b0};
                end
            end
        end
    end
endmodule

`default_nettype wire
