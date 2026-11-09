`timescale 1ns / 1ps
`default_nettype none

// MMCM2 reconfiguration sequencer (SPEC 7.7): waits for clk_fast to be on the safe clock,
// starts the reconfiguration, then waits for lock.  Never overlaps a running image: the
// caller blocks START while busy is high.
module clk_seq #(
    parameter LEVELS_LOG2 = 4
) (
    input  wire                   clk,
    input  wire                   rst,
    input  wire                   request,
    input  wire [LEVELS_LOG2-1:0] level,
    input  wire                   is_turbo,
    input  wire                   reconfig_busy,
    input  wire                   turbo_locked,
    output reg                    busy,
    output reg                    reconfig_start,
    output reg  [LEVELS_LOG2-1:0] reconfig_level
);
    localparam [1:0] S_IDLE = 2'd0, S_WAIT_SAFE = 2'd1, S_STARTED = 2'd2, S_WAIT_LOCK = 2'd3;
    reg [1:0] state;
    reg [3:0] settle;

    always @(posedge clk) begin
        reconfig_start <= 1'b0;
        if (rst) begin
            state          <= S_IDLE;
            busy           <= 1'b0;
            settle         <= 4'd0;
            reconfig_level <= {LEVELS_LOG2{1'b0}};
        end else begin
            case (state)
                S_IDLE: if (request) begin
                    reconfig_level <= level;
                    busy           <= 1'b1;
                    state          <= S_WAIT_SAFE;
                end
                S_WAIT_SAFE: if (!is_turbo) begin
                    reconfig_start <= 1'b1;
                    settle         <= 4'd8;
                    state          <= S_STARTED;
                end
                // Give the generator time to raise its busy flag.
                S_STARTED: begin
                    settle <= settle - 1'b1;
                    if (settle == 4'd0) state <= S_WAIT_LOCK;
                end
                S_WAIT_LOCK: if (!reconfig_busy && turbo_locked) begin
                    busy  <= 1'b0;
                    state <= S_IDLE;
                end
                default: state <= S_IDLE;
            endcase
        end
    end
endmodule

`default_nettype wire
