`timescale 1ns / 1ps
`default_nettype none

// Bank of 32-bit event counters in distributed RAM.  One increment per cycle, read
// asynchronously by the host.  clear sweeps every entry to zero, one per cycle.
module counter_bank #(
    parameter AW = 7
) (
    input  wire          clk,
    input  wire          rst,
    input  wire          clear,
    output wire          clearing,
    input  wire          inc,
    input  wire [AW-1:0] inc_addr,
    input  wire [AW-1:0] rd_addr,
    output wire [31:0]   rd_data
);
    reg [31:0] mem [0:(1<<AW)-1];
    reg [AW:0] sweep;

    wire [AW-1:0] sweep_addr = sweep[AW-1:0];
    assign clearing = ~sweep[AW];
    assign rd_data  = mem[rd_addr];

    always @(posedge clk) begin
        if (rst) sweep <= {(AW+1){1'b1}};
        else if (clear) sweep <= {(AW+1){1'b0}};
        else if (clearing) sweep <= sweep + 1'b1;

        if (clearing & ~rst) mem[sweep_addr] <= 32'd0;
        else if (inc) mem[inc_addr] <= mem[inc_addr] + 1'b1;
    end
endmodule

`default_nettype wire
