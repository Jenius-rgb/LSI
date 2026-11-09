`timescale 1ns / 1ps
`default_nettype none

// SENTINEL accelerator core.  clk_safe holds memories, control, operand generation,
// checking, post-processing and pooling; clk_fast holds the MAC lanes (SPEC 7).
// clk_fast is selected by the clock generator outside this module.
//
// Layer sequencing comes from the runtime-loadable layer table (model/export.py).
// Failing recompute units go to a log and are recomputed at the safe clock once the layer
// has finished (SPEC 9).
module engine #(
    parameter K          = 8,
    parameter R          = 2,
    parameter C3_EN      = 0,
    parameter LANE_IMPL  = 0,
    parameter INJ_EN     = 1,
    parameter INJ_SLOTS  = 2,
    parameter ACC_W      = 32,
    parameter ACC_CS_W   = 48,
    parameter WC1_W      = 11,
    parameter WC2_W      = 14,
    parameter WC3_W      = 16,
    parameter WEIGHT_AW  = 12,
    parameter ACT0_AW    = 13,
    parameter ACT1_AW    = 12,
    parameter IMG_AW     = 12,
    parameter PARAM_AW   = 9,
    parameter LOG_AW     = 8,
    parameter MAX_LAYERS = 8,
    parameter OPF_LOG2   = 4,
    parameter INFO_LOG2  = 3,
    parameter LAYER_TABLE_INDEX = 256
) (
    input  wire                  clk_safe,
    input  wire                  clk_fast,
    input  wire                  rst,

    input  wire                  start,
    input  wire [1:0]            mode,
    input  wire                  c3_on,
    input  wire                  trust_csum,
    input  wire                  img_sel,
    input  wire [MAX_LAYERS-1:0] turbo_mask,

    output reg                   clk_sel_turbo,
    input  wire                  clk_is_turbo,

    input  wire                  host_en,
    input  wire                  host_we,
    input  wire [23:0]           host_addr,
    input  wire [7:0]            host_wdata,
    output reg  [7:0]            host_rdata,

    input  wire [INJ_SLOTS-1:0]         inj_en,
    input  wire [INJ_SLOTS-1:0]         inj_any,
    input  wire [INJ_SLOTS-1:0]         inj_oneshot,
    input  wire [INJ_SLOTS*4-1:0]       inj_layer,
    input  wire [INJ_SLOTS*16-1:0]      inj_unit,
    input  wire [INJ_SLOTS*6-1:0]       inj_lane,
    input  wire [INJ_SLOTS*ACC_CS_W-1:0] inj_mask,

    output reg                   busy,
    output reg                   done,
    output reg                   fatal,
    output reg                   log_ovf,
    output reg  [3:0]            result_class,
    output reg  [31:0]           cycles_total,
    output reg  [31:0]           cycles_recompute,
    output wire [31:0]           starve_cycles,
    output reg                   image_done,
    output reg  [MAX_LAYERS-1:0] gov_fail_mask,
    output reg  [15:0]           gov_corr_total,
    output reg  [15:0]           lane_status,

    input  wire [6:0]            cnt_addr,
    output wire [31:0]           cnt_data
);
    localparam integer KB     = $clog2(K);
    localparam integer G_W    = 6;
    localparam integer WIN_W  = 4;
    localparam integer ACT_AW = 13;
    localparam integer NCS    = 2 + (C3_EN != 0 ? 1 : 0);
    localparam integer WORDS  = K + NCS;
    localparam integer SET_W  = 2 + 8 + K*8 + WC1_W + WC2_W + (C3_EN != 0 ? WC3_W : 0);
    localparam integer OPF_W  = R * (SET_W + 1);
    localparam integer OPF_SLICES = (OPF_W + 49) / 50;
    localparam integer MAX_OUT_LOG2  = INFO_LOG2;
    localparam integer RESF_LOG2     = $clog2(WORDS * (1 << MAX_OUT_LOG2));
    localparam integer SB_W  = G_W + KB + 2*WIN_W + 2 + 1;

    localparam [2:0] O_NONE = 3'd0, O_CLEAN = 3'd1, O_CORRECTED = 3'd2, O_CSUM = 3'd3, O_RECOMPUTE = 3'd4;

    // Counter bank layout: {layer, type} for per-layer counters, then per-lane correction counters.
    localparam [2:0] C_UNITS = 3'd0, C_CLEAN = 3'd1, C_CORRECTED = 3'd2, C_CSUM = 3'd3, C_RECOMPUTE = 3'd4, C_FATAL = 3'd5;

    // ---- memories ---------------------------------------------------------------------
    wire [WEIGHT_AW-1:0] gen_w_addr0, gen_w_addr1;
    wire [K*8-1:0]       w_dout_a, w_dout_b;
    wire [ACT_AW-1:0]    gen_a_addr0, gen_a_addr1;

    reg  [31:0]          host_param_dummy;

    wire [7:0] img_dout_a [0:1];
    wire [7:0] img_dout_b [0:1];
    wire [7:0] act_dout_a [0:1];
    wire [7:0] act_dout_b [0:1];

    wire host_is_w  = (host_addr[23:16] == 8'h01);
    wire host_is_p  = (host_addr[23:16] == 8'h02);
    wire host_is_i0 = (host_addr[23:14] == 10'b0000001100);
    wire host_is_i1 = (host_addr[23:14] == 10'b0000001101);
    wire host_is_l  = (host_addr[23:16] == 8'h04);

    wire [KB-1:0] host_lane = host_addr[KB-1:0];

    // Weights: engine reads through both ports; the host writes bytes on port A when idle.
    wire [K-1:0] w_we = (host_en & host_we & host_is_w & ~busy) ? ({{(K-1){1'b0}}, 1'b1} << host_lane) : {K{1'b0}};
    wire [WEIGHT_AW-1:0] host_w_word = host_addr[WEIGHT_AW-1+KB:KB];

    ram_tdp #(.ADDR_W(WEIGHT_AW), .NB_COL(K), .COL_W(8)) u_wram (
        .clk(clk_safe),
        .en_a(1'b1),
        .we_a(w_we),
        .addr_a(busy ? gen_w_addr0 : host_w_word),
        .din_a({K{host_wdata}}),
        .dout_a(w_dout_a),
        .en_b(1'b1),
        .addr_b(gen_w_addr1),
        .dout_b(w_dout_b));

    // Bias and layer table: 32-bit words, host on port A, engine on port B.
    wire [3:0]            p_we = (host_en & host_we & host_is_p & ~busy) ? (4'b0001 << host_addr[1:0]) : 4'b0000;
    wire [PARAM_AW-1:0]   host_p_word = host_addr[PARAM_AW+1:2];
    wire [31:0]           p_dout_a, p_dout_b;
    reg  [PARAM_AW-1:0]   p_addr_b;

    ram_tdp #(.ADDR_W(PARAM_AW), .NB_COL(4), .COL_W(8)) u_pram (
        .clk(clk_safe),
        .en_a(1'b1),
        .we_a(p_we),
        .addr_a(host_p_word),
        .din_a({4{host_wdata}}),
        .dout_a(p_dout_a),
        .en_b(1'b1),
        .addr_b(p_addr_b),
        .dout_b(p_dout_b));

    reg  [15:0] cfg_cout;
    reg         cfg_is_fc;
    reg  [1:0]  cfg_src_sel, cfg_dst_sel;
    reg  [3:0]  cfg_log2w;
    reg  [15:0] cfg_t, cfg_g;
    reg  [WEIGHT_AW-1:0] cfg_wbase;
    reg  [PARAM_AW-1:0]  cfg_bbase;
    reg  [ACT_AW-1:0]    cfg_src_base, cfg_dst_base;
    reg  [15:0] cfg_m;
    reg  [4:0]  cfg_n;

    wire engine_reads_img0 = busy & (cfg_src_sel == 2'd0) & ~img_sel;
    wire engine_reads_img1 = busy & (cfg_src_sel == 2'd0) &  img_sel;

    wire [IMG_AW-1:0] host_img_addr = host_addr[IMG_AW-1:0];

    ram_tdp #(.ADDR_W(IMG_AW)) u_img0 (
        .clk(clk_safe), .en_a(1'b1),
        .we_a(host_en & host_we & host_is_i0 & ~engine_reads_img0),
        .addr_a(engine_reads_img0 ? gen_a_addr0[IMG_AW-1:0] : host_img_addr),
        .din_a(host_wdata), .dout_a(img_dout_a[0]),
        .en_b(1'b1), .addr_b(gen_a_addr1[IMG_AW-1:0]), .dout_b(img_dout_b[0]));

    ram_tdp #(.ADDR_W(IMG_AW)) u_img1 (
        .clk(clk_safe), .en_a(1'b1),
        .we_a(host_en & host_we & host_is_i1 & ~engine_reads_img1),
        .addr_a(engine_reads_img1 ? gen_a_addr0[IMG_AW-1:0] : host_img_addr),
        .din_a(host_wdata), .dout_a(img_dout_a[1]),
        .en_b(1'b1), .addr_b(gen_a_addr1[IMG_AW-1:0]), .dout_b(img_dout_b[1]));

    // Activation buffers.  Port A: output writes when the buffer is the destination,
    // otherwise operand reads; port B: operand reads.
    reg                out_we;
    reg  [ACT_AW-1:0]  out_addr;
    reg  [7:0]         out_data;

    wire act0_dst = (cfg_dst_sel == 2'd1);
    wire act1_dst = (cfg_dst_sel == 2'd2);

    ram_tdp #(.ADDR_W(ACT0_AW)) u_act0 (
        .clk(clk_safe), .en_a(1'b1),
        .we_a(out_we & act0_dst),
        .addr_a(act0_dst ? out_addr[ACT0_AW-1:0] : gen_a_addr0[ACT0_AW-1:0]),
        .din_a(out_data), .dout_a(act_dout_a[0]),
        .en_b(1'b1), .addr_b(gen_a_addr1[ACT0_AW-1:0]), .dout_b(act_dout_b[0]));

    ram_tdp #(.ADDR_W(ACT1_AW)) u_act1 (
        .clk(clk_safe), .en_a(1'b1),
        .we_a(out_we & act1_dst),
        .addr_a(act1_dst ? out_addr[ACT1_AW-1:0] : gen_a_addr0[ACT1_AW-1:0]),
        .din_a(out_data), .dout_a(act_dout_a[1]),
        .en_b(1'b1), .addr_b(gen_a_addr1[ACT1_AW-1:0]), .dout_b(act_dout_b[1]));

    wire [7:0] src_data0 = (cfg_src_sel == 2'd0) ? img_dout_a[img_sel] : act_dout_a[cfg_src_sel[1]];
    wire [7:0] src_data1 = (cfg_src_sel == 2'd0) ? img_dout_b[img_sel] : act_dout_b[cfg_src_sel[1]];

    // Logits: N_CLASSES_MAX int32 values.
    reg  [31:0] logits [0:15];
    reg  [3:0]  logit_scan;

    // Host byte read path, 2 cycles after host_en.
    reg [4:0]  host_sel_r;
    reg [KB-1:0] host_lane_r;
    reg [1:0]  host_byte_r;
    wire [31:0] logit_word = logits[host_addr[5:2]];
    reg [31:0]  logit_word_r;
    wire [8:0]  w_lane_bit = {{(6-KB){1'b0}}, host_lane_r, 3'b000};
    wire [K*8-1:0] w_shifted = w_dout_a >> w_lane_bit;
    wire [4:0]  p_byte_bit = {host_byte_r, 3'b000};
    wire [31:0] p_shifted = p_dout_a >> p_byte_bit;
    wire [31:0] l_shifted = logit_word_r >> p_byte_bit;

    always @(posedge clk_safe) begin
        host_sel_r  <= {host_is_l, host_is_i1, host_is_i0, host_is_p, host_is_w};
        host_lane_r <= host_lane;
        host_byte_r <= host_addr[1:0];
        logit_word_r <= logit_word;
        case (1'b1)
            host_sel_r[0]: host_rdata <= w_shifted[7:0];
            host_sel_r[1]: host_rdata <= p_shifted[7:0];
            host_sel_r[2]: host_rdata <= img_dout_a[0];
            host_sel_r[3]: host_rdata <= img_dout_a[1];
            host_sel_r[4]: host_rdata <= l_shifted[7:0];
            default:       host_rdata <= 8'd0;
        endcase
        host_param_dummy <= p_dout_a;
    end

    // ---- operand generation -----------------------------------------------------------
    reg                 gen_start;
    reg                 gen_use_log;
    wire                gen_busy;
    wire [LOG_AW-1:0]   gen_log_addr;
    wire [G_W+2*WIN_W-1:0] log_rdata;
    reg  [LOG_AW:0]     log_count;

    wire                opf_wr;
    wire [OPF_W-1:0]    opf_wdata;
    wire                opf_afull;
    wire                info_wr;
    wire [G_W+2*WIN_W+2-1:0] info_wdata;
    wire                info_full;

    operand_gen #(
        .K(K), .R(R), .C3_EN(C3_EN), .WC1_W(WC1_W), .WC2_W(WC2_W), .WC3_W(WC3_W),
        .WEIGHT_AW(WEIGHT_AW), .ACT_AW(ACT_AW), .G_W(G_W), .WIN_W(WIN_W), .LOG_AW(LOG_AW)
    ) u_gen (
        .clk(clk_safe), .rst(rst),
        .cfg_is_fc(cfg_is_fc), .cfg_t(cfg_t), .cfg_g(cfg_g), .cfg_log2w(cfg_log2w),
        .cfg_wbase(cfg_wbase), .cfg_src_base(cfg_src_base),
        .start(gen_start), .use_log(gen_use_log), .log_count(log_count),
        .log_addr(gen_log_addr), .log_data(log_rdata), .busy(gen_busy),
        .act_addr0(gen_a_addr0), .act_addr1(gen_a_addr1),
        .act_data0(src_data0), .act_data1(src_data1),
        .w_addr0(gen_w_addr0), .w_addr1(gen_w_addr1),
        .w_data0(w_dout_a), .w_data1(w_dout_b),
        .fifo_wr(opf_wr), .fifo_data(opf_wdata), .fifo_afull(opf_afull),
        .info_wr(info_wr), .info_data(info_wdata), .info_full(info_full));

    // Reset for clk_fast logic, synchronized into that domain.
    reg [2:0] rst_fast_sync;
    always @(posedge clk_fast) rst_fast_sync <= {rst_fast_sync[1:0], rst};
    wire rst_fast = rst_fast_sync[2];

    // ---- clock-domain crossing ---------------------------------------------------------
    wire              opf_empty, opf_rd;
    wire [OPF_W-1:0]  opf_rdata;
    wire              resf_empty, resf_wr, resf_afull;
    reg               resf_rd;
    wire [ACC_CS_W-1:0] resf_wdata, resf_rdata;

    cdc_fifo #(.WIDTH(OPF_W), .DEPTH_LOG2(OPF_LOG2), .AFULL_MARGIN(6), .SLICES(OPF_SLICES)) u_opfifo (
        .wr_clk(clk_safe), .wr_rst(rst), .wr_en(opf_wr), .wr_data(opf_wdata), .afull(opf_afull),
        .rd_clk(clk_fast), .rd_rst(rst_fast), .rd_en(opf_rd), .rd_data(opf_rdata), .empty(opf_empty));

    cdc_fifo #(.WIDTH(ACC_CS_W), .DEPTH_LOG2(RESF_LOG2), .AFULL_MARGIN(1)) u_resfifo (
        .wr_clk(clk_fast), .wr_rst(rst_fast), .wr_en(resf_wr), .wr_data(resf_wdata), .afull(resf_afull),
        .rd_clk(clk_safe), .rd_rst(rst), .rd_en(resf_rd), .rd_data(resf_rdata), .empty(resf_empty));

    // ---- fast domain ------------------------------------------------------------------
    reg                  pass_active;
    reg  [3:0]           layer;
    reg                  pass_recompute;

    reg [INJ_SLOTS-1:0]  inj_layer_match;
    integer il;
    always @* begin
        for (il = 0; il < INJ_SLOTS; il = il + 1)
            inj_layer_match[il] = inj_en[il] & (inj_layer[il*4 +: 4] == layer);
    end

    fast_path #(
        .K(K), .R(R), .C3_EN(C3_EN), .WC1_W(WC1_W), .WC2_W(WC2_W), .WC3_W(WC3_W),
        .ACC_W(ACC_W), .ACC_CS_W(ACC_CS_W), .LANE_IMPL(LANE_IMPL), .INJ_EN(INJ_EN), .INJ_SLOTS(INJ_SLOTS)
    ) u_fast (
        .clk(clk_fast), .rst(rst_fast),
        .op_empty(opf_empty), .op_data(opf_rdata), .op_rd(opf_rd),
        .res_valid(resf_wr), .res_data(resf_wdata),
        .pass_active(pass_active), .starve_cycles(starve_cycles),
        .inj_en(inj_layer_match), .inj_any(inj_any), .inj_oneshot(inj_oneshot),
        .inj_rearm((layer == 4'd0) & ~pass_recompute),
        .inj_unit(inj_unit), .inj_lane(inj_lane), .inj_mask(inj_mask));

    // ---- result side: FIFO -> checker -> post-processing ------------------------------
    wire                chk_in_ready, chk_done;
    wire [2:0]          chk_outcome;
    wire [4:0]          chk_lane;
    reg  [4:0]          chk_y_addr;
    wire [ACC_W-1:0]    chk_y_data;
    reg                 chk_ack;

    wire chk_in_valid = ~resf_empty & chk_in_ready;
    always @* resf_rd = chk_in_valid;

    lane_checker #(.K(K), .C3_EN(C3_EN), .ACC_W(ACC_W), .ACC_CS_W(ACC_CS_W)) u_checker (
        .clk(clk_safe), .rst(rst), .mode(mode), .trust_csum_lane(trust_csum), .c3_on(c3_on),
        .in_valid(chk_in_valid), .in_data(resf_rdata), .in_ready(chk_in_ready),
        .done(chk_done), .outcome(chk_outcome), .lane(chk_lane),
        .y_addr(chk_y_addr), .y_data(chk_y_data), .ack(chk_ack));

    // Unit bookkeeping: what each unit in flight is.
    localparam integer INFO_W = G_W + 2*WIN_W + 2;
    reg [INFO_W-1:0] info_mem [0:(1<<INFO_LOG2)-1];
    reg [INFO_LOG2:0] info_wp, info_rp;
    wire info_empty = (info_wp == info_rp);
    assign info_full = ((info_wp[INFO_LOG2] != info_rp[INFO_LOG2]) &&
                        (info_wp[INFO_LOG2-1:0] == info_rp[INFO_LOG2-1:0]));
    wire [INFO_W-1:0] info_head = info_mem[info_rp[INFO_LOG2-1:0]];
    wire [G_W-1:0]    head_g   = info_head[INFO_W-1 -: G_W];
    wire [WIN_W-1:0]  head_wy  = info_head[WIN_W*2+1 -: WIN_W];
    wire [WIN_W-1:0]  head_wx  = info_head[WIN_W+1 -: WIN_W];
    wire [1:0]        head_pos = info_head[1:0];

    reg              r_post;
    reg [KB:0]       r_k;
    reg [G_W-1:0]    r_g;
    reg [WIN_W-1:0]  r_wy, r_wx;
    reg [1:0]        r_pos;
    reg              r_window_end;

    reg                post_valid_in;
    reg  [SB_W-1:0]    post_sb_in;
    wire               post_v_valid, post_out_valid, post_busy;
    wire signed [32:0] post_v;
    wire [SB_W-1:0]    post_v_sb, post_out_sb;
    wire [7:0]         post_out;

    postproc #(.ACC_W(ACC_W), .SB_W(SB_W)) u_post (
        .clk(clk_safe), .rst(rst),
        .in_valid(post_valid_in), .y(chk_y_data), .b(p_dout_b),
        .m(cfg_m), .n(cfg_n), .in_sb(post_sb_in),
        .v_valid(post_v_valid), .v(post_v), .v_sb(post_v_sb),
        .out_valid(post_out_valid), .out(post_out), .out_sb(post_out_sb), .busy(post_busy));

    wire [G_W-1:0]   pv_g  = post_v_sb[SB_W-1 -: G_W];
    wire [KB-1:0]    pv_k  = post_v_sb[SB_W-1-G_W -: KB];
    wire             pv_fc = post_v_sb[0];

    wire [G_W-1:0]   po_g   = post_out_sb[SB_W-1 -: G_W];
    wire [KB-1:0]    po_k   = post_out_sb[SB_W-1-G_W -: KB];
    wire [WIN_W-1:0] po_wy  = post_out_sb[2*WIN_W+2 -: WIN_W];
    wire [WIN_W-1:0] po_wx  = post_out_sb[WIN_W+2 -: WIN_W];
    wire [1:0]       po_pos = post_out_sb[2:1];
    wire             po_fc  = post_out_sb[0];

    wire [7:0] pooled;
    pool #(.K(K)) u_pool (
        .clk(clk_safe), .valid(post_out_valid & ~po_fc), .lane(po_k), .pos(po_pos),
        .value(post_out), .pooled(pooled));

    wire [G_W+KB-1:0] po_o  = {po_g, po_k};
    wire [15:0]       po_o_ext = {{(16-G_W-KB){1'b0}}, po_o};
    wire [G_W+KB-1:0] pv_o  = {pv_g, pv_k};
    wire [15:0]       pv_o_ext = {{(16-G_W-KB){1'b0}}, pv_o};
    wire [3:0]        m2 = cfg_log2w - 1'b1;
    wire [4:0]        m2_double = {m2, 1'b0};
    wire [ACT_AW-1:0] o_addr  = {{(ACT_AW-G_W-KB){1'b0}}, po_o};
    wire [ACT_AW-1:0] wy_addr = {{(ACT_AW-WIN_W){1'b0}}, po_wy};
    wire [ACT_AW-1:0] wx_addr = {{(ACT_AW-WIN_W){1'b0}}, po_wx};

    always @(posedge clk_safe) begin
        out_we   <= post_out_valid & ~po_fc & (po_pos == 2'd3) & (po_o_ext < cfg_cout);
        out_addr <= cfg_dst_base + (o_addr << m2_double) + (wy_addr << m2) + wx_addr;
        out_data <= pooled;
        if (post_v_valid & pv_fc & (pv_o_ext < cfg_cout))
            logits[pv_o[3:0]] <= post_v[31:0];
    end

    // ---- recompute log ------------------------------------------------------------------
    reg                       log_wr;
    reg  [G_W+2*WIN_W-1:0]    log_wdata;
    wire [G_W+2*WIN_W-1:0]    log_dout_a;

    ram_tdp #(.ADDR_W(LOG_AW), .NB_COL(1), .COL_W(G_W+2*WIN_W)) u_log (
        .clk(clk_safe), .en_a(1'b1), .we_a(log_wr), .addr_a(log_count[LOG_AW-1:0]),
        .din_a(log_wdata), .dout_a(log_dout_a),
        .en_b(1'b1), .addr_b(gen_log_addr), .dout_b(log_rdata));

    localparam [LOG_AW:0] LOG_DEPTH = {1'b1, {LOG_AW{1'b0}}};

    // ---- counters -----------------------------------------------------------------------
    reg         cnt_clear;
    wire        cnt_clearing;
    reg         cnt_inc;
    reg  [6:0]  cnt_inc_addr;
    counter_bank #(.AW(7)) u_counters (
        .clk(clk_safe), .rst(rst), .clear(cnt_clear), .clearing(cnt_clearing),
        .inc(cnt_inc), .inc_addr(cnt_inc_addr),
        .rd_addr(cnt_addr), .rd_data(cnt_data));

    localparam integer LANE_COUNTER_BASE = 64;

    // ---- control ------------------------------------------------------------------------
    localparam [3:0] S_IDLE = 4'd0, S_CLEAR = 4'd1, S_LOAD = 4'd2, S_CLK = 4'd3, S_CLK_WAIT = 4'd4,
                     S_START = 4'd5, S_RUN = 4'd6, S_DRAIN = 4'd7, S_EVAL = 4'd8, S_NEXT = 4'd9,
                     S_SCAN = 4'd10, S_FINISH = 4'd11;
    reg [3:0] state;
    reg [3:0] rec_idx;
    reg [3:0] rec_idx_d;
    reg       rec_valid_d;

    reg             window_fail;
    reg             log_full_flag;
    reg [1:0]       inc_phase;
    reg [2:0]       latched_outcome;
    reg [4:0]       latched_lane;

    reg [3:0]              best_idx;
    reg signed [31:0]      best_val;
    wire signed [31:0]     scan_val = logits[logit_scan];

    wire outstanding_clear = info_empty & ~r_post & ~post_busy & ~post_valid_in & ~out_we;

    wire [KB-1:0] r_k_low = r_k[KB-1:0];
    wire [G_W+KB-1:0]  r_o = {r_g, r_k_low};
    wire [PARAM_AW-1:0] r_o_ext = {{(PARAM_AW-G_W-KB){1'b0}}, r_o};

    wire this_failed = (latched_outcome == O_RECOMPUTE);

    always @* begin
        if (state == S_LOAD) p_addr_b = LAYER_TABLE_INDEX[PARAM_AW-1:0] + {{(PARAM_AW-7){1'b0}}, layer, 3'b000} + {{(PARAM_AW-4){1'b0}}, rec_idx};
        else                 p_addr_b = cfg_bbase + r_o_ext;
    end

    always @(posedge clk_safe) begin
        gen_start     <= 1'b0;
        done          <= 1'b0;
        image_done    <= 1'b0;
        cnt_clear     <= 1'b0;
        cnt_inc       <= 1'b0;
        log_wr        <= 1'b0;
        chk_ack       <= 1'b0;
        post_valid_in <= 1'b0;

        if (rst) begin
            state          <= S_IDLE;
            busy           <= 1'b0;
            fatal          <= 1'b0;
            log_ovf        <= 1'b0;
            result_class   <= 4'd0;
            cycles_total   <= 32'd0;
            cycles_recompute <= 32'd0;
            clk_sel_turbo  <= 1'b0;
            pass_active    <= 1'b0;
            pass_recompute <= 1'b0;
            layer          <= 4'd0;
            rec_idx        <= 4'd0;
            rec_idx_d      <= 4'd0;
            rec_valid_d    <= 1'b0;
            info_wp        <= {(INFO_LOG2+1){1'b0}};
            info_rp        <= {(INFO_LOG2+1){1'b0}};
            r_post         <= 1'b0;
            r_k            <= {(KB+1){1'b0}};
            inc_phase      <= 2'd0;
            window_fail    <= 1'b0;
            log_count      <= {(LOG_AW+1){1'b0}};
            log_full_flag  <= 1'b0;
            logit_scan     <= 4'd0;
            best_idx       <= 4'd0;
            gen_use_log    <= 1'b0;
            chk_y_addr     <= 5'd0;
            gov_fail_mask  <= {MAX_LAYERS{1'b0}};
            gov_corr_total <= 16'd0;
            lane_status    <= 16'd0;
        end else begin
            if (busy) cycles_total <= cycles_total + 1'b1;
            if (busy & pass_recompute) cycles_recompute <= cycles_recompute + 1'b1;

            // Unit bookkeeping.
            if (info_wr) begin
                info_mem[info_wp[INFO_LOG2-1:0]] <= info_wdata;
                info_wp <= info_wp + 1'b1;
            end
            if (chk_done) begin
                info_rp         <= info_rp + 1'b1;
                latched_outcome <= chk_outcome;
                latched_lane    <= chk_lane;
                r_g             <= head_g;
                r_wy            <= head_wy;
                r_wx            <= head_wx;
                r_pos           <= head_pos;
                r_window_end    <= cfg_is_fc | (head_pos == 2'd3);
                r_post          <= 1'b1;
                r_k             <= {(KB+1){1'b0}};
                inc_phase       <= 2'd1;
            end

            // Counter updates for the unit just decided: up to three increments.
            if (inc_phase != 2'd0) begin
                inc_phase <= (inc_phase == 2'd3) ? 2'd0 : inc_phase + 1'b1;
                if (!pass_recompute) begin
                    if (inc_phase == 2'd1) begin
                        cnt_inc      <= 1'b1;
                        cnt_inc_addr <= {layer, C_UNITS};
                    end else if (inc_phase == 2'd2) begin
                        case (latched_outcome)
                            O_CLEAN: begin cnt_inc <= 1'b1; cnt_inc_addr <= {layer, C_CLEAN}; end
                            O_CORRECTED: begin
                                cnt_inc      <= 1'b1;
                                cnt_inc_addr <= {layer, C_CORRECTED};
                                lane_status[latched_lane[3:0] - 1'b1] <= 1'b1;
                                if (gov_corr_total != 16'hFFFF) gov_corr_total <= gov_corr_total + 1'b1;
                            end
                            O_CSUM: begin cnt_inc <= 1'b1; cnt_inc_addr <= {layer, C_CSUM}; end
                            O_RECOMPUTE: begin
                                cnt_inc                  <= 1'b1;
                                cnt_inc_addr             <= {layer, C_RECOMPUTE};
                                gov_fail_mask[layer[2:0]] <= 1'b1;
                            end
                            default: ;
                        endcase
                    end else if (latched_outcome == O_CORRECTED) begin
                        cnt_inc      <= 1'b1;
                        cnt_inc_addr <= LANE_COUNTER_BASE[6:0] + {2'b00, latched_lane} - 1'b1;
                    end
                end else if (inc_phase == 2'd1 && latched_outcome != O_CLEAN && latched_outcome != O_NONE) begin
                    cnt_inc      <= 1'b1;
                    cnt_inc_addr <= {layer, C_FATAL};
                    fatal        <= 1'b1;
                end
            end

            // Failure tracking and log writes: one entry per failing recompute unit.
            if (inc_phase == 2'd1 && !pass_recompute) begin
                if (r_window_end) begin
                    window_fail <= 1'b0;
                    if (window_fail | this_failed) begin
                        if (log_count != LOG_DEPTH) begin
                            log_wr    <= 1'b1;
                            log_wdata <= {r_g, r_wy, r_wx};
                        end else begin
                            log_full_flag <= 1'b1;
                        end
                    end
                end else if (this_failed) begin
                    window_fail <= 1'b1;
                end
            end
            if (log_wr) log_count <= log_count + 1'b1;

            // Post-processing issue: one lane per cycle, K cycles.
            if (r_post) begin
                post_valid_in <= 1'b1;
                post_sb_in    <= {r_g, r_k_low, r_wy, r_wx, r_pos, cfg_is_fc};
                chk_y_addr    <= {{(5-KB){1'b0}}, r_k_low};
                if (r_k_low == {KB{1'b1}}) begin
                    r_post  <= 1'b0;
                    chk_ack <= 1'b1;
                end
                r_k <= r_k + 1'b1;
            end

            rec_valid_d <= 1'b0;

            case (state)
                S_IDLE: begin
                    busy <= 1'b0;
                    if (start) begin
                        busy             <= 1'b1;
                        fatal            <= 1'b0;
                        log_ovf          <= 1'b0;
                        cycles_total     <= 32'd0;
                        cycles_recompute <= 32'd0;
                        layer            <= 4'd0;
                        cnt_clear        <= 1'b1;
                        gov_fail_mask    <= {MAX_LAYERS{1'b0}};
                        gov_corr_total   <= 16'd0;
                        lane_status      <= 16'd0;
                        state            <= S_CLEAR;
                    end
                end

                S_CLEAR: if (!cnt_clear && !cnt_clearing) begin
                    rec_idx <= 4'd0;
                    state   <= S_LOAD;
                end

                S_LOAD: begin
                    rec_idx_d   <= rec_idx;
                    rec_valid_d <= (rec_idx != 4'd8);
                    if (rec_idx == 4'd8) begin
                        state <= S_CLK;
                    end else begin
                        rec_idx <= rec_idx + 1'b1;
                    end
                end

                S_CLK: begin
                    // SPEC 7.7: sel only changes here, between passes, with the fast domain idle.
                    clk_sel_turbo <= pass_recompute ? 1'b0 : turbo_mask[layer[2:0]];
                    state         <= S_CLK_WAIT;
                end

                S_CLK_WAIT: if (clk_is_turbo == clk_sel_turbo) begin
                    state <= S_START;
                end

                S_START: begin
                    gen_start   <= 1'b1;
                    pass_active <= 1'b1;
                    state       <= S_RUN;
                end

                S_RUN: if (!gen_start && !gen_busy) begin
                    state <= S_DRAIN;
                end

                S_DRAIN: if (outstanding_clear) begin
                    pass_active <= 1'b0;
                    state       <= S_EVAL;
                end

                S_EVAL: begin
                    if (pass_recompute | (mode == 2'd0)) begin
                        pass_recompute <= 1'b0;
                        state          <= S_NEXT;
                    end else if (log_full_flag) begin
                        log_ovf        <= 1'b1;
                        cnt_inc        <= 1'b1;
                        cnt_inc_addr   <= LANE_COUNTER_BASE[6:0] + 7'd20;
                        gen_use_log    <= 1'b0;
                        pass_recompute <= 1'b1;
                        state          <= S_CLK;
                    end else if (log_count != {(LOG_AW+1){1'b0}}) begin
                        gen_use_log    <= 1'b1;
                        pass_recompute <= 1'b1;
                        state          <= S_CLK;
                    end else begin
                        state          <= S_NEXT;
                    end
                end

                S_NEXT: begin
                    log_count     <= {(LOG_AW+1){1'b0}};
                    log_full_flag <= 1'b0;
                    gen_use_log   <= 1'b0;
                    if (cfg_is_fc) begin
                        logit_scan <= 4'd0;
                        best_idx   <= 4'd0;
                        state      <= S_SCAN;
                    end else begin
                        layer   <= layer + 1'b1;
                        rec_idx <= 4'd0;
                        state   <= S_LOAD;
                    end
                end

                S_SCAN: begin
                    if (logit_scan == 4'd0 || scan_val > best_val) begin
                        best_val <= scan_val;
                        best_idx <= logit_scan;
                    end
                    if ({12'd0, logit_scan} == cfg_cout - 1'b1) begin
                        state <= S_FINISH;
                    end else begin
                        logit_scan <= logit_scan + 1'b1;
                    end
                end

                S_FINISH: begin
                    result_class <= best_idx;
                    clk_sel_turbo <= 1'b0;
                    done         <= 1'b1;
                    image_done   <= 1'b1;
                    busy         <= 1'b0;
                    state        <= S_IDLE;
                end

                default: state <= S_IDLE;
            endcase

            if (rec_valid_d) begin
                case (rec_idx_d)
                    4'd0: begin
                        cfg_is_fc   <= p_dout_b[0];
                        cfg_src_sel <= p_dout_b[3:2];
                        cfg_dst_sel <= p_dout_b[5:4];
                        cfg_log2w   <= p_dout_b[11:8];
                    end
                    4'd1: cfg_cout <= p_dout_b[31:16];
                    4'd3: begin
                        cfg_t <= p_dout_b[15:0];
                        cfg_g <= p_dout_b[31:16];
                    end
                    4'd4: cfg_wbase <= p_dout_b[WEIGHT_AW-1:0];
                    4'd5: cfg_bbase <= p_dout_b[PARAM_AW-1:0];
                    4'd6: begin
                        cfg_src_base <= p_dout_b[ACT_AW-1:0];
                        cfg_dst_base <= p_dout_b[16+ACT_AW-1:16];
                    end
                    4'd7: begin
                        cfg_m <= p_dout_b[15:0];
                        cfg_n <= p_dout_b[20:16];
                    end
                    default: ;
                endcase
            end
        end
    end

    wire unused_engine = &{1'b0, host_param_dummy, log_dout_a, w_shifted, p_shifted, l_shifted,
                           host_addr[23:16], post_v, cfg_src_sel, chk_lane, latched_lane, resf_afull, post_v_sb};
endmodule

`default_nettype wire
