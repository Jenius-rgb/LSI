`timescale 1ns / 1ps
`default_nettype none

// Everything in clk_fast (SPEC 7.2): reads wide operand words, serializes the R slots,
// drives the lane array and writes the result words.
//
// Registers separate the FIFO output, the slot mux and the broadcast to the lanes so that
// the MAC paths stay critical (SPEC 7.4).  STARVE counts cycles with no operand ready
// while a pass is running (pass_active is synchronized from clk_safe).
module fast_path #(
    parameter K         = 8,
    parameter R         = 2,
    parameter C3_EN     = 0,
    parameter W_W       = 8,
    parameter WC1_W     = 11,
    parameter WC2_W     = 14,
    parameter WC3_W     = 16,
    parameter ACC_W     = 32,
    parameter ACC_CS_W  = 48,
    parameter LANE_IMPL = 0,
    parameter INJ_EN    = 1,
    parameter INJ_SLOTS = 2,
    parameter UNIT_W    = 16,
    parameter LANE_ID_W = 6
) (
    input  wire                 clk,
    input  wire                 rst,
    input  wire                 op_empty,
    input  wire [R*(2+8+K*W_W+WC1_W+WC2_W+(C3_EN!=0?WC3_W:0)+1)-1:0] op_data,
    output wire                 op_rd,
    output wire                 res_valid,
    output wire [ACC_CS_W-1:0]  res_data,
    input  wire                 pass_active,
    output reg  [31:0]          starve_cycles,
    input  wire [INJ_SLOTS-1:0]           inj_en,
    input  wire [INJ_SLOTS-1:0]           inj_any,
    input  wire [INJ_SLOTS-1:0]           inj_oneshot,
    input  wire                           inj_rearm,
    input  wire [INJ_SLOTS*UNIT_W-1:0]    inj_unit,
    input  wire [INJ_SLOTS*LANE_ID_W-1:0] inj_lane,
    input  wire [INJ_SLOTS*ACC_CS_W-1:0]  inj_mask
);
    localparam integer WC_FIELD = WC1_W + WC2_W + (C3_EN != 0 ? WC3_W : 0);
    localparam integer SET_W  = 2 + 8 + K*W_W + WC_FIELD;
    localparam integer SLOT_W = SET_W + 1;

    reg [R*SLOT_W-1:0] word;
    reg                word_valid;
    reg                slot;

    wire [SLOT_W-1:0] slot0 = word[SLOT_W-1:0];
    wire [SLOT_W-1:0] slot1 = word[R*SLOT_W-1 -: SLOT_W];

    wire on_last_slot = (R == 1) | slot | ~slot1[SLOT_W-1];
    wire can_take     = ~word_valid | on_last_slot;

    assign op_rd = ~op_empty & can_take;

    reg [SET_W-1:0] set_r;
    reg             set_valid;

    wire pass_active_sync;
    reg  pass_s1, pass_s2;
    always @(posedge clk) begin
        pass_s1 <= pass_active;
        pass_s2 <= pass_s1;
    end
    assign pass_active_sync = pass_s2;

    always @(posedge clk) begin
        if (rst) begin
            word_valid    <= 1'b0;
            slot          <= 1'b0;
            set_valid     <= 1'b0;
            starve_cycles <= 32'd0;
        end else begin
            if (can_take) begin
                word_valid <= ~op_empty;
                slot       <= 1'b0;
            end else begin
                slot <= 1'b1;
            end
            set_valid <= word_valid;
            if (pass_active_sync & ~word_valid & op_empty)
                starve_cycles <= starve_cycles + 1'b1;
        end
        if (can_take) word <= op_data;
        set_r <= (R == 2 && slot) ? slot1[SET_W-1:0] : slot0[SET_W-1:0];
    end

    wire [K*W_W-1:0]  set_w     = set_r[WC_FIELD +: K*W_W];
    wire [7:0]        set_a     = set_r[WC_FIELD+K*W_W +: 8];
    wire              set_last  = set_r[WC_FIELD+K*W_W+8];
    wire              set_pass  = set_r[WC_FIELD+K*W_W+9];
    wire [WC1_W-1:0]  set_wc1   = set_r[WC1_W-1:0];
    wire [WC2_W-1:0]  set_wc2   = set_r[WC1_W +: WC2_W];
    wire [WC3_W-1:0]  set_wc3;

    generate
        if (C3_EN != 0) begin : with_c3
            assign set_wc3 = set_r[WC1_W+WC2_W +: WC3_W];
        end else begin : no_c3
            assign set_wc3 = {WC3_W{1'b0}};
        end
    endgenerate

    lane_array #(
        .K(K), .C3_EN(C3_EN), .W_W(W_W), .WC1_W(WC1_W), .WC2_W(WC2_W), .WC3_W(WC3_W),
        .ACC_W(ACC_W), .ACC_CS_W(ACC_CS_W), .LANE_IMPL(LANE_IMPL),
        .INJ_EN(INJ_EN), .INJ_SLOTS(INJ_SLOTS), .UNIT_W(UNIT_W), .LANE_ID_W(LANE_ID_W)
    ) u_lanes (
        .clk(clk), .rst(rst),
        .op_valid(set_valid), .op_last(set_last), .op_pass_start(set_pass),
        .op_a(set_a), .op_w(set_w), .op_wc1(set_wc1), .op_wc2(set_wc2), .op_wc3(set_wc3),
        .inj_en(inj_en), .inj_any(inj_any), .inj_oneshot(inj_oneshot), .inj_rearm(inj_rearm),
        .inj_unit(inj_unit), .inj_lane(inj_lane), .inj_mask(inj_mask),
        .res_valid(res_valid), .res_data(res_data)
    );

    wire unused_word = &{1'b0, slot0[SLOT_W-1], slot1};
endmodule

`default_nettype wire
