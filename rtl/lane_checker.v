`timescale 1ns / 1ps
`default_nettype none

// Checksum comparator and corrector (SPEC 6.2, 6.3, 6.4).
//
// Words arrive as S1, S2, (S3), YK .. Y1.  Three chained accumulators (A += Y, B += A,
// C += B) give A = sum(Y), B = sum(k*Y) and sum(k*k*Y) = 2C - B without multipliers.
// The search for j is sequential and division-free: j*d1 and j*j*d1 are accumulated.
//
// Latency after the last word: 2 cycles for a decision without search, plus up to K cycles
// of search and 1 cycle to write the correction.
module lane_checker #(
    parameter K         = 8,
    parameter C3_EN     = 0,
    parameter ACC_W     = 32,
    parameter ACC_CS_W  = 48,
    parameter LANE_BITS = 5
) (
    input  wire                 clk,
    input  wire                 rst,
    input  wire [1:0]           mode,
    input  wire                 trust_csum_lane,
    input  wire                 c3_on,
    input  wire                 in_valid,
    input  wire [ACC_CS_W-1:0]  in_data,
    output wire                 in_ready,
    output reg                  done,
    output reg  [2:0]           outcome,
    output reg  [LANE_BITS-1:0] lane,
    input  wire [LANE_BITS-1:0] y_addr,
    output wire [ACC_W-1:0]     y_data,
    input  wire                 ack
);
    localparam NCS   = 2 + (C3_EN != 0 ? 1 : 0);
    localparam WORDS = K + NCS;
    localparam IDX_W = $clog2(K);

    // Values of model.checker.Outcome.
    localparam [2:0] O_NONE = 3'd0, O_CLEAN = 3'd1, O_CORRECTED = 3'd2, O_CSUM = 3'd3, O_RECOMPUTE = 3'd4;

    localparam [2:0] S_RECV = 3'd0, S_CALC = 3'd1, S_JUDGE = 3'd2, S_SEARCH = 3'd3, S_FIX = 3'd4, S_HOLD = 3'd5;

    reg [2:0] state;
    reg [6:0] count;

    reg [ACC_CS_W-1:0] s1, s2, s3;
    reg [ACC_CS_W-1:0] sum_a, sum_b, sum_c;
    reg [ACC_CS_W-1:0] d1, d2, d3;
    reg [ACC_CS_W-1:0] j_d1, jj_d1, step;
    reg [LANE_BITS-1:0] j;

    reg [ACC_W-1:0] y_mem [0:K-1];
    assign y_data = y_mem[y_addr[IDX_W-1:0]];

    assign in_ready = (state == S_RECV);

    wire c3_active = (C3_EN != 0) & c3_on;
    wire d1_nz = |d1;
    wire d2_nz = |d2;
    wire d3_nz = |d3;

    wire [6:0] y_index = count - NCS[6:0];              // 0 for YK, K-1 for Y1
    wire [ACC_CS_W-1:0] a_next = sum_a + in_data;
    wire [ACC_CS_W-1:0] b_next = sum_b + a_next;
    wire [ACC_CS_W-1:0] c_next = sum_c + b_next;
    wire [ACC_CS_W-1:0] sum_k2 = (sum_c << 1) - sum_b;

    wire match = (d2 == j_d1) & (~c3_active | (d3 == jj_d1));

    // Result of the trust_csum_lane branch of SPEC 6.2.
    reg [2:0]           tail_outcome;
    reg [LANE_BITS-1:0] tail_lane;
    always @* begin
        tail_outcome = O_RECOMPUTE;
        tail_lane    = {LANE_BITS{1'b0}};
        if (trust_csum_lane) begin
            if (d1_nz & ~d2_nz & ~d3_nz) begin
                tail_outcome = O_CSUM;
                tail_lane    = {{(LANE_BITS-1){1'b0}}, 1'b1};
            end else if (~d1_nz & d2_nz & ~d3_nz) begin
                tail_outcome = O_CSUM;
                tail_lane    = {{(LANE_BITS-2){1'b0}}, 2'd2};
            end else if (c3_active & ~d1_nz & ~d2_nz & d3_nz) begin
                tail_outcome = O_CSUM;
                tail_lane    = {{(LANE_BITS-2){1'b0}}, 2'd3};
            end
        end
    end

    wire [IDX_W-1:0] fix_index = j[IDX_W-1:0] - 1'b1;
    wire [ACC_W-1:0]     fix_value = y_mem[fix_index] - d1[ACC_W-1:0];

    // Reversed lane address of the incoming data word.
    wire [IDX_W-1:0] y_write_idx = (K[IDX_W-1:0] - 1'b1) - y_index[IDX_W-1:0];
    wire unused_upper = &{1'b0, y_addr[LANE_BITS-1:IDX_W], y_index[6:IDX_W]};

    always @(posedge clk) begin
        if (state == S_RECV && in_valid && count >= NCS[6:0])
            y_mem[y_write_idx] <= in_data[ACC_W-1:0];
        else if (state == S_FIX)
            y_mem[fix_index] <= fix_value;
    end

    always @(posedge clk) begin
        done <= 1'b0;
        if (rst) begin
            state   <= S_RECV;
            count   <= 7'd0;
            sum_a   <= {ACC_CS_W{1'b0}};
            sum_b   <= {ACC_CS_W{1'b0}};
            sum_c   <= {ACC_CS_W{1'b0}};
            outcome <= O_NONE;
            lane    <= {LANE_BITS{1'b0}};
        end else begin
            case (state)
                S_RECV: if (in_valid) begin
                    if (count == 7'd0) s1 <= in_data;
                    else if (count == 7'd1) s2 <= in_data;
                    else if (count < NCS[6:0]) s3 <= in_data;
                    else begin
                        sum_a <= a_next;
                        sum_b <= b_next;
                        sum_c <= c_next;
                    end
                    if (count == WORDS[6:0] - 1'b1) begin
                        count <= 7'd0;
                        state <= S_CALC;
                    end else begin
                        count <= count + 1'b1;
                    end
                end

                S_CALC: begin
                    d1 <= sum_a - s1;
                    d2 <= sum_b - s2;
                    d3 <= c3_active ? (sum_k2 - s3) : {ACC_CS_W{1'b0}};
                    state <= S_JUDGE;
                end

                S_JUDGE: begin
                    lane <= {LANE_BITS{1'b0}};
                    if (mode == 2'd0) begin
                        outcome <= O_NONE;
                        state   <= S_HOLD;
                        done    <= 1'b1;
                    end else if (mode == 2'd1) begin
                        outcome <= d1_nz ? O_RECOMPUTE : O_CLEAN;
                        state   <= S_HOLD;
                        done    <= 1'b1;
                    end else if (~d1_nz & ~d2_nz & ~d3_nz) begin
                        outcome <= O_CLEAN;
                        state   <= S_HOLD;
                        done    <= 1'b1;
                    end else if (d1_nz) begin
                        j     <= {{(LANE_BITS-1){1'b0}}, 1'b1};
                        j_d1  <= d1;
                        jj_d1 <= d1;
                        step  <= (d1 << 1) + d1;
                        state <= S_SEARCH;
                    end else begin
                        outcome <= tail_outcome;
                        lane    <= tail_lane;
                        state   <= S_HOLD;
                        done    <= 1'b1;
                    end
                end

                S_SEARCH: begin
                    if (match) begin
                        state <= S_FIX;
                    end else if (j == K[LANE_BITS-1:0]) begin
                        outcome <= tail_outcome;
                        lane    <= tail_lane;
                        state   <= S_HOLD;
                        done    <= 1'b1;
                    end else begin
                        j     <= j + 1'b1;
                        j_d1  <= j_d1 + d1;
                        jj_d1 <= jj_d1 + step;
                        step  <= step + (d1 << 1);
                    end
                end

                S_FIX: begin
                    outcome <= O_CORRECTED;
                    lane    <= j;
                    state   <= S_HOLD;
                    done    <= 1'b1;
                end

                S_HOLD: if (ack) begin
                    sum_a <= {ACC_CS_W{1'b0}};
                    sum_b <= {ACC_CS_W{1'b0}};
                    sum_c <= {ACC_CS_W{1'b0}};
                    state <= S_RECV;
                end

                default: state <= S_RECV;
            endcase
        end
    end
endmodule

`default_nettype wire
