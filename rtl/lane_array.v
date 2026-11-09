`timescale 1ns / 1ps
`default_nettype none

// K data lanes plus 2 or 3 checksum lanes, holding registers and result serializer.
//
// A unit's results leave as K + NCS words of ACC_CS_W bits, in the order
// S1, S2, (S3), YK .. Y1, data words sign-extended.  Descending lane order lets the checker
// form the weighted sums with adders only (see rtl/lane_checker.v).  The chain is a shift
// register, so the fast clock only ever sees a 2:1 mux in front of each holding register.
// Spec 7.3 requires K + 3 <= T, which guarantees the chain has drained before the next
// unit finishes.
//
// Fault injection (SPEC 11.1) XORs a holding register when its unit is captured.  The unit
// counter restarts on op_pass_start, so injection sees indices local to the current pass.
// inj_* inputs are quasi-static: they only change while this domain is idle.
module lane_array #(
    parameter K         = 8,
    parameter C3_EN     = 0,
    parameter W_W       = 8,
    parameter WC1_W     = 11,
    parameter WC2_W     = 14,
    parameter WC3_W     = 16,
    parameter ACC_W     = 32,
    parameter ACC_CS_W  = 48,
    parameter LANE_IMPL = 0,      // 0 = lut, 1 = dsp_min, 2 = dsp_full
    parameter INJ_EN    = 1,
    parameter INJ_SLOTS = 2,
    parameter UNIT_W    = 16,
    parameter LANE_ID_W = 6
) (
    input  wire                            clk,
    input  wire                            rst,
    input  wire                            op_valid,
    input  wire                            op_last,
    input  wire                            op_pass_start,
    input  wire [7:0]                      op_a,
    input  wire [K*W_W-1:0]                op_w,
    input  wire [WC1_W-1:0]                op_wc1,
    input  wire [WC2_W-1:0]                op_wc2,
    input  wire [WC3_W-1:0]                op_wc3,
    input  wire [INJ_SLOTS-1:0]            inj_en,
    input  wire [INJ_SLOTS-1:0]            inj_any,
    input  wire [INJ_SLOTS-1:0]            inj_oneshot,
    input  wire                            inj_rearm,
    input  wire [INJ_SLOTS*UNIT_W-1:0]     inj_unit,
    input  wire [INJ_SLOTS*LANE_ID_W-1:0]  inj_lane,
    input  wire [INJ_SLOTS*ACC_CS_W-1:0]   inj_mask,
    output wire                            res_valid,
    output wire [ACC_CS_W-1:0]             res_data
);
    localparam NCS   = 2 + (C3_EN != 0 ? 1 : 0);
    localparam WORDS = K + NCS;

    wire [K*ACC_W-1:0]     y_acc;
    wire [K-1:0]           y_last;
    wire [NCS*ACC_CS_W-1:0] s_acc;
    wire [NCS-1:0]         s_last;

    // Checksum weights on a uniform bus, each sign-extended to the widest one.
    wire [3*WC3_W-1:0] wc_bus = {op_wc3,
                                 {(WC3_W-WC2_W){op_wc2[WC2_W-1]}}, op_wc2,
                                 {(WC3_W-WC1_W){op_wc1[WC1_W-1]}}, op_wc1};

    genvar gi;
    generate
        for (gi = 0; gi < K; gi = gi + 1) begin : data_lane
            wire signed [W_W-1:0] lane_w = op_w[gi*W_W +: W_W];
            if (LANE_IMPL == 0) begin : impl
                lane_lut #(.W_W(W_W), .ACC_W(ACC_W)) u (
                    .clk(clk), .rst(rst), .valid(op_valid), .last(op_last), .a(op_a), .w(lane_w),
                    .acc(y_acc[gi*ACC_W +: ACC_W]), .acc_last(y_last[gi]));
            end else if (LANE_IMPL == 1) begin : impl
                lane_dsp_min #(.W_W(W_W), .ACC_W(ACC_W)) u (
                    .clk(clk), .rst(rst), .valid(op_valid), .last(op_last), .a(op_a), .w(lane_w),
                    .acc(y_acc[gi*ACC_W +: ACC_W]), .acc_last(y_last[gi]));
            end else begin : impl
                lane_dsp_full #(.W_W(W_W), .ACC_W(ACC_W)) u (
                    .clk(clk), .rst(rst), .valid(op_valid), .last(op_last), .a(op_a), .w(lane_w),
                    .acc(y_acc[gi*ACC_W +: ACC_W]), .acc_last(y_last[gi]));
            end
        end

        for (gi = 0; gi < NCS; gi = gi + 1) begin : csum_lane
            localparam CW = (gi == 0) ? WC1_W : (gi == 1) ? WC2_W : WC3_W;
            wire signed [CW-1:0] lane_w = wc_bus[gi*WC3_W +: CW];
            if (LANE_IMPL == 0) begin : impl
                lane_lut #(.W_W(CW), .ACC_W(ACC_CS_W)) u (
                    .clk(clk), .rst(rst), .valid(op_valid), .last(op_last), .a(op_a), .w(lane_w),
                    .acc(s_acc[gi*ACC_CS_W +: ACC_CS_W]), .acc_last(s_last[gi]));
            end else if (LANE_IMPL == 1) begin : impl
                lane_dsp_min #(.W_W(CW), .ACC_W(ACC_CS_W)) u (
                    .clk(clk), .rst(rst), .valid(op_valid), .last(op_last), .a(op_a), .w(lane_w),
                    .acc(s_acc[gi*ACC_CS_W +: ACC_CS_W]), .acc_last(s_last[gi]));
            end else begin : impl
                lane_dsp_full #(.W_W(CW), .ACC_W(ACC_CS_W)) u (
                    .clk(clk), .rst(rst), .valid(op_valid), .last(op_last), .a(op_a), .w(lane_w),
                    .acc(s_acc[gi*ACC_CS_W +: ACC_CS_W]), .acc_last(s_last[gi]));
            end
        end
    endgenerate

    // All lanes share the same latency; lane 0 stands for all of them.
    wire capture = y_last[0];
    wire unused_lane_status = &{1'b0, wc_bus};

    // ---- fault injection --------------------------------------------------------------
    reg [UNIT_W-1:0]    unit;
    reg [INJ_SLOTS-1:0] fired;
    reg [INJ_SLOTS-1:0] fire_r;
    reg [WORDS-1:0]     lane_fire [0:INJ_SLOTS-1];   // registered per lane to keep fanout low
    integer             ls, lm;

    integer s;
    reg [INJ_SLOTS-1:0] unit_match;
    reg [INJ_SLOTS-1:0] fire_next;
    always @* begin
        fire_next = {INJ_SLOTS{1'b0}};
        for (s = 0; s < INJ_SLOTS; s = s + 1)
            fire_next[s] = inj_en[s] & ~(inj_oneshot[s] & fired[s]) & unit_match[s];
    end

    generate
        if (INJ_EN != 0) begin : inj_ctrl
            // unit only changes at a capture, and captures are at least T cycles apart,
            // so fire_r is settled well before it is used.
            always @(posedge clk) begin
                fire_r <= fire_next;
                for (ls = 0; ls < INJ_SLOTS; ls = ls + 1) begin
                    unit_match[ls] <= inj_any[ls] | (unit == inj_unit[ls*UNIT_W +: UNIT_W]);
                    for (lm = 0; lm < WORDS; lm = lm + 1)
                        lane_fire[ls][lm] <= fire_next[ls] & (inj_lane[ls*LANE_ID_W +: LANE_ID_W] == (lm[LANE_ID_W-1:0] + 1'b1));
                end
                if (rst) begin
                    unit   <= {UNIT_W{1'b0}};
                    fired  <= {INJ_SLOTS{1'b0}};
                end else begin
                    if (op_valid & op_pass_start) unit <= {UNIT_W{1'b0}};
                    else if (capture) unit <= unit + 1'b1;
                    if (op_valid & op_pass_start & inj_rearm) fired <= {INJ_SLOTS{1'b0}};
                    else if (capture) fired <= fired | fire_r;
                end
            end
        end else begin : inj_ctrl
            always @(posedge clk) begin
                unit   <= {UNIT_W{1'b0}};
                fired  <= {INJ_SLOTS{1'b0}};
                fire_r <= {INJ_SLOTS{1'b0}};
                unit_match <= {INJ_SLOTS{1'b0}};
                for (ls = 0; ls < INJ_SLOTS; ls = ls + 1)
                    lane_fire[ls] <= {WORDS{1'b0}};
            end
        end
    endgenerate

    // ---- holding registers and serializer ---------------------------------------------
    // Checksum words sit at the head of the chain: only these positions need ACC_CS_W bits.
    reg [ACC_CS_W-1:0] hold_cs [0:NCS-1];
    reg [ACC_W-1:0]    hold_y  [0:K-1];
    reg [6:0]          remaining;
    reg                valid_r;

    wire [ACC_CS_W-1:0] y_head_ext = {{(ACC_CS_W-ACC_W){hold_y[0][ACC_W-1]}}, hold_y[0]};

    assign res_valid = valid_r;
    assign res_data  = hold_cs[0];

    // XOR masks per lane, numbered 1..K for data lanes and K+1.. for checksum lanes.
    reg [ACC_CS_W-1:0] mask_cs [0:NCS-1];
    reg [ACC_W-1:0]    mask_y  [0:K-1];
    reg [ACC_CS_W-1:0] mask_id;
    integer m, t;
    always @* begin
        for (m = 0; m < WORDS; m = m + 1) begin
            mask_id = {ACC_CS_W{1'b0}};
            for (t = 0; t < INJ_SLOTS; t = t + 1)
                if (lane_fire[t][m])
                    mask_id = mask_id ^ inj_mask[t*ACC_CS_W +: ACC_CS_W];
            if (m < K) mask_y[m] = mask_id[ACC_W-1:0];
            else       mask_cs[m-K] = mask_id;
        end
    end

    integer i;
    always @(posedge clk) begin
        // Each holding register is loaded by its own lane's finish pulse, which keeps the
        // select fanout local.  The chain shifts freely; res_valid qualifies its output.
        for (i = 0; i < NCS - 1; i = i + 1)
            hold_cs[i] <= s_last[i] ? (s_acc[i*ACC_CS_W +: ACC_CS_W] ^ mask_cs[i]) : hold_cs[i+1];
        hold_cs[NCS-1] <= s_last[NCS-1] ? (s_acc[(NCS-1)*ACC_CS_W +: ACC_CS_W] ^ mask_cs[NCS-1]) : y_head_ext;
        for (i = 0; i < K - 1; i = i + 1)
            hold_y[i] <= y_last[K-1-i] ? (y_acc[(K-1-i)*ACC_W +: ACC_W] ^ mask_y[K-1-i]) : hold_y[i+1];
        if (y_last[0]) hold_y[K-1] <= y_acc[ACC_W-1:0] ^ mask_y[0];

        if (rst) begin
            remaining <= 7'd0;
            valid_r   <= 1'b0;
        end else if (capture) begin
            remaining <= WORDS[6:0];
            valid_r   <= 1'b1;
        end else if (remaining > 7'd1) begin
            remaining <= remaining - 1'b1;
        end else begin
            remaining <= 7'd0;
            valid_r   <= 1'b0;
        end
    end
endmodule

`default_nettype wire
