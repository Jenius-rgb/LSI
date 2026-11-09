`timescale 1ns / 1ps

// Replays a transaction log written by LogTransport into the SPI port of top_core
// (SPEC 12.6) and compares every byte the driver expected.  SCLK runs at f_safe / 8.
module tb_spi_log;
    parameter K = 8;
    parameter C3_EN = 0;
    parameter WC1_W = 11;
    parameter WC2_W = 14;
    parameter WC3_W = 16;
    parameter WEIGHT_AW = 11;
    parameter ACT0_AW = 12;
    parameter ACT1_AW = 10;
    parameter MAX_LOG = 400000;

    localparam SAFE_NS = 10.0;

    reg rst = 1;
    reg sclk = 0, cs_n = 1, mosi = 0;
    wire miso;
    wire [3:0] led;

    top_core #(.K(K), .C3_EN(C3_EN), .WC1_W(WC1_W), .WC2_W(WC2_W), .WC3_W(WC3_W),
               .WEIGHT_AW(WEIGHT_AW), .ACT0_AW(ACT0_AW), .ACT1_AW(ACT1_AW)) dut (
        .clk_in(1'b0), .rst(rst), .spi_sclk(sclk), .spi_cs_n(cs_n), .spi_mosi(mosi), .spi_miso(miso), .led(led));

    reg [31:0] log [0:MAX_LOG-1];
    reg [8*200-1:0] path;

    integer pc, errors, checks, polls;
    reg [31:0] entry;
    reg [7:0] rx;

    task xfer;
        input  [7:0] tx;
        output [7:0] got;
        integer b;
        begin
            for (b = 7; b >= 0; b = b - 1) begin
                mosi = tx[b];
                #(4 * SAFE_NS);
                sclk = 1;
                got[b] = miso;
                #(4 * SAFE_NS);
                sclk = 0;
            end
        end
    endtask

    // Polls the low byte of a register until (byte & mask) == value.
    task poll;
        input [7:0] offset;
        input [7:0] mask;
        input [7:0] value;
        reg [7:0] data;
        reg [7:0] tmp;
        reg       found;
        begin
            found = 0;
            while (!found) begin
                polls = polls + 1;
                cs_n = 0;
                #(4 * SAFE_NS);
                xfer(8'h03, tmp); xfer(8'h00, tmp); xfer(8'h00, tmp); xfer(offset, tmp);
                xfer(8'h00, tmp);
                xfer(8'h00, data);
                #(4 * SAFE_NS);
                cs_n = 1;
                #(8 * SAFE_NS);
                if ((data & mask) == value) found = 1;
                if (polls > 2000000) begin
                    $display("FAIL poll timeout");
                    $fatal(1);
                end
            end
        end
    endtask

    initial begin
        if (!$value$plusargs("log=%s", path)) begin $display("FAIL no log"); $fatal(1); end
        $readmemh(path, log);
        errors = 0;
        checks = 0;
        polls = 0;
        #(100 * SAFE_NS);
        rst = 0;
        #(100 * SAFE_NS);
        pc = 0;
        while (log[pc][31:24] !== 8'hFF) begin
            entry = log[pc];
            case (entry[31:24])
                8'h01: begin
                    xfer(entry[23:16], rx);
                    if (entry[7:0] != 8'h00) begin
                        checks = checks + 1;
                        if ((rx & entry[7:0]) !== (entry[15:8] & entry[7:0])) begin
                            if (errors == 0)
                                $display("FAIL log_entry=%0d lane=- expected=%h got=%h tx=%h", pc, entry[15:8], rx, entry[23:16]);
                            errors = errors + 1;
                        end
                    end
                end
                8'h02: begin
                    cs_n = 0;
                    #(4 * SAFE_NS);
                end
                8'h03: begin
                    #(4 * SAFE_NS);
                    cs_n = 1;
                    #(16 * SAFE_NS);
                end
                8'h04: poll(entry[23:16], entry[15:8], entry[7:0]);
                default: begin
                    $display("FAIL bad log op %h at %0d", entry[31:24], pc);
                    $fatal(1);
                end
            endcase
            pc = pc + 1;
        end
        #(100 * SAFE_NS);
        if (errors != 0) begin
            $display("FAIL errors=%0d of %0d", errors, checks);
            $fatal(1);
        end
        $display("PASS %0d/%0d polls=%0d", checks, checks, polls);
        $finish;
    end
endmodule
