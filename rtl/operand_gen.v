`timescale 1ns / 1ps
`default_nettype none

// Operand generator (SPEC 5.3): walks the loops of a layer and reads activations and
// weights, producing up to R operand sets per clk_safe cycle for the operand FIFO.
//
// A pass is either the whole layer or, for a recompute pass, the windows listed in the log.
// Pipeline: address registers -> RAM outputs -> (wc adder tree, 2 stages) -> FIFO write.
//
// FIFO word: R slots, each {valid, set}; a set is {pass_start, last, a, w[K], wc3, wc2, wc1}.
// wc3 is omitted when C3_EN = 0.
module operand_gen #(
    parameter K         = 8,
    parameter R         = 2,
    parameter C3_EN     = 0,
    parameter W_W       = 8,
    parameter WC1_W     = 11,
    parameter WC2_W     = 14,
    parameter WC3_W     = 16,
    parameter WEIGHT_AW = 12,
    parameter ACT_AW    = 13,
    parameter G_W       = 6,
    parameter WIN_W     = 4,
    parameter LOG_AW    = 8
) (
    input  wire                  clk,
    input  wire                  rst,

    input  wire                  cfg_is_fc,
    input  wire [15:0]           cfg_t,
    input  wire [15:0]           cfg_g,
    input  wire [3:0]            cfg_log2w,
    input  wire [WEIGHT_AW-1:0]  cfg_wbase,
    input  wire [ACT_AW-1:0]     cfg_src_base,

    input  wire                  start,
    input  wire                  use_log,
    input  wire [LOG_AW:0]       log_count,
    output reg  [LOG_AW-1:0]     log_addr,
    input  wire [G_W+2*WIN_W-1:0] log_data,
    output wire                  busy,

    output wire [ACT_AW-1:0]     act_addr0,
    output wire [ACT_AW-1:0]     act_addr1,
    input  wire [7:0]            act_data0,
    input  wire [7:0]            act_data1,
    output wire [WEIGHT_AW-1:0]  w_addr0,
    output wire [WEIGHT_AW-1:0]  w_addr1,
    input  wire [K*W_W-1:0]      w_data0,
    input  wire [K*W_W-1:0]      w_data1,

    output wire                  fifo_wr,
    output wire [R*(2+8+K*W_W+WC1_W+WC2_W+(C3_EN!=0?WC3_W:0)+1)-1:0] fifo_data,
    input  wire                  fifo_afull,

    output wire                  info_wr,
    output wire [G_W+2*WIN_W+2-1:0] info_data,
    input  wire                  info_full
);
    localparam integer SET_W  = 2 + 8 + K*W_W + WC1_W + WC2_W + (C3_EN != 0 ? WC3_W : 0);
    localparam integer SLOT_W = SET_W + 1;
    localparam integer MW     = 12;

    localparam [2:0] S_IDLE = 3'd0, S_RUN = 3'd1, S_LOG_ADDR = 3'd2, S_LOG_DATA = 3'd3, S_LOG_NEXT = 3'd4;
    reg [2:0] state;

    reg [G_W-1:0]   g;
    reg [WIN_W-1:0] wy, wx;
    reg [1:0]       pos;
    reg [15:0]      t;
    reg [15:0]      c;
    reg [1:0]       i, j;
    reg             pass_first;
    reg [WEIGHT_AW-1:0] w_base_g;

    assign busy = (state != S_IDLE);

    // ---- slot positions ---------------------------------------------------------------
    wire        j0_last = (j == 2'd2);
    wire        i0_last = (i == 2'd2);
    wire [1:0]  j1 = j0_last ? 2'd0 : j + 1'b1;
    wire [1:0]  i1 = j0_last ? (i0_last ? 2'd0 : i + 1'b1) : i;
    wire [15:0] c1 = (j0_last & i0_last) ? c + 1'b1 : c;
    wire        j1_last = (j1 == 2'd2);
    wire        i1_last = (i1 == 2'd2);
    wire [1:0]  j2 = j1_last ? 2'd0 : j1 + 1'b1;
    wire [1:0]  i2 = j1_last ? (i1_last ? 2'd0 : i1 + 1'b1) : i1;
    wire [15:0] c2 = (j1_last & i1_last) ? c1 + 1'b1 : c1;

    wire [15:0] t_last  = cfg_t - 1'b1;
    wire        two     = (R == 2) && (t != t_last);
    wire [15:0] t_after = t + (two ? 16'd2 : 16'd1);
    wire        unit_end = (t_after == cfg_t);

    // ---- loop exits -------------------------------------------------------------------
    wire [WIN_W-1:0] win_max = cfg_is_fc ? {WIN_W{1'b0}}
                                         : (({{(WIN_W-1){1'b0}}, 1'b1} << (cfg_log2w - 1'b1)) - 1'b1);
    wire [G_W-1:0]   g_max = cfg_g[G_W-1:0] - 1'b1;
    wire pos_last   = cfg_is_fc ? 1'b1 : (pos == 2'd3);
    wire wx_last    = (wx == win_max);
    wire wy_last    = (wy == win_max);
    wire g_last     = (g == g_max);
    wire window_end = unit_end & pos_last;
    wire pass_end   = window_end & wx_last & wy_last & g_last;

    // ---- address generation -----------------------------------------------------------
    wire [WIN_W:0] y = {wy, pos[1]};
    wire [WIN_W:0] x = {wx, pos[0]};

    wire [6:0] yy0 = {1'b0, y} + {4'b0, i}  + 7'h7f;
    wire [6:0] xx0 = {1'b0, x} + {4'b0, j}  + 7'h7f;
    wire [6:0] yy1 = {1'b0, y} + {4'b0, i1} + 7'h7f;
    wire [6:0] xx1 = {1'b0, x} + {4'b0, j1} + 7'h7f;

    wire pad0 = ~cfg_is_fc & (|(yy0 >> cfg_log2w) | |(xx0 >> cfg_log2w));
    wire pad1 = ~cfg_is_fc & (|(yy1 >> cfg_log2w) | |(xx1 >> cfg_log2w));

    wire [ACT_AW-1:0] c0_ext  = c[ACT_AW-1:0];
    wire [ACT_AW-1:0] c1_ext  = c1[ACT_AW-1:0];
    wire [ACT_AW-1:0] yy0_ext = {{(ACT_AW-7){1'b0}}, yy0};
    wire [ACT_AW-1:0] yy1_ext = {{(ACT_AW-7){1'b0}}, yy1};
    wire [ACT_AW-1:0] xx0_ext = {{(ACT_AW-7){1'b0}}, xx0};
    wire [ACT_AW-1:0] xx1_ext = {{(ACT_AW-7){1'b0}}, xx1};
    wire [4:0]        m2      = {cfg_log2w, 1'b0};

    // Address stage 1: everything that depends on the loop state.  Stage 2 only sums.
    reg [ACT_AW-1:0] a0_base, a0_row, a0_col, a1_base, a1_row, a1_col;
    reg [WEIGHT_AW-1:0] w0_addr_r, w1_addr_r;
    reg [1:0] pad_a;

    always @(posedge clk) begin
        a0_base   <= cfg_is_fc ? cfg_src_base : cfg_src_base + (c0_ext << m2);
        a1_base   <= cfg_is_fc ? cfg_src_base : cfg_src_base + (c1_ext << m2);
        a0_row    <= cfg_is_fc ? t[ACT_AW-1:0] : (yy0_ext << cfg_log2w);
        a1_row    <= cfg_is_fc ? t[ACT_AW-1:0] + 1'b1 : (yy1_ext << cfg_log2w);
        a0_col    <= cfg_is_fc ? {ACT_AW{1'b0}} : xx0_ext;
        a1_col    <= cfg_is_fc ? {ACT_AW{1'b0}} : xx1_ext;
        w0_addr_r <= w_base_g + t[WEIGHT_AW-1:0];
        w1_addr_r <= w_base_g + t[WEIGHT_AW-1:0] + 1'b1;
        pad_a     <= {pad1, pad0};
    end

    assign act_addr0 = a0_base + a0_row + a0_col;
    assign act_addr1 = a1_base + a1_row + a1_col;
    assign w_addr0   = w0_addr_r;
    assign w_addr1   = w1_addr_r;

    // ---- flow control -----------------------------------------------------------------
    wire new_unit = (t == 16'd0);
    wire advance  = (state == S_RUN) & ~fifo_afull & (~new_unit | ~info_full);

    assign info_wr   = advance & new_unit;
    assign info_data = {g, wy, wx, pos};

    wire [G_W-1:0]   log_g  = log_data[G_W+2*WIN_W-1:2*WIN_W];
    wire [WIN_W-1:0] log_wy = log_data[2*WIN_W-1:WIN_W];
    wire [WIN_W-1:0] log_wx = log_data[WIN_W-1:0];

    wire [MW-1:0] t_ext = cfg_t[MW-1:0];

    // verilator lint_off UNUSEDSIGNAL
    function [WEIGHT_AW-1:0] group_base;
        input [G_W-1:0] group;
        input [MW-1:0]  unit_t;
        input [WEIGHT_AW-1:0] base;
        reg [G_W+MW-1:0] product;
        begin
            product = group * unit_t;
            group_base = base + product[WEIGHT_AW-1:0];
        end
    endfunction
    // verilator lint_on UNUSEDSIGNAL

    always @(posedge clk) begin
        if (rst) begin
            state      <= S_IDLE;
            t          <= 16'd0;
            c          <= 16'd0;
            i          <= 2'd0;
            j          <= 2'd0;
            pos        <= 2'd0;
            g          <= {G_W{1'b0}};
            wy         <= {WIN_W{1'b0}};
            wx         <= {WIN_W{1'b0}};
            log_addr   <= {LOG_AW{1'b0}};
            pass_first <= 1'b0;
            w_base_g   <= {WEIGHT_AW{1'b0}};
        end else begin
            case (state)
                S_IDLE: if (start) begin
                    t          <= 16'd0;
                    c          <= 16'd0;
                    i          <= 2'd0;
                    j          <= 2'd0;
                    pos        <= 2'd0;
                    g          <= {G_W{1'b0}};
                    wy         <= {WIN_W{1'b0}};
                    wx         <= {WIN_W{1'b0}};
                    log_addr   <= {LOG_AW{1'b0}};
                    pass_first <= 1'b1;
                    w_base_g   <= cfg_wbase;
                    state      <= use_log ? S_LOG_ADDR : S_RUN;
                end

                S_LOG_ADDR: state <= S_LOG_DATA;

                S_LOG_DATA: begin
                    g        <= log_g;
                    wy       <= log_wy;
                    wx       <= log_wx;
                    pos      <= 2'd0;
                    w_base_g <= group_base(log_g, t_ext, cfg_wbase);
                    state    <= S_RUN;
                end

                S_LOG_NEXT: begin
                    log_addr <= log_addr + 1'b1;
                    if ({1'b0, log_addr} + 1'b1 == log_count) state <= S_IDLE;
                    else state <= S_LOG_ADDR;
                end

                S_RUN: if (advance) begin
                    pass_first <= 1'b0;
                    if (unit_end) begin
                        t <= 16'd0;
                        c <= 16'd0;
                        i <= 2'd0;
                        j <= 2'd0;
                        if (!pos_last) begin
                            pos <= pos + 1'b1;
                        end else begin
                            pos <= 2'd0;
                            if (use_log) begin
                                state <= S_LOG_NEXT;
                            end else if (!wx_last) begin
                                wx <= wx + 1'b1;
                            end else begin
                                wx <= {WIN_W{1'b0}};
                                if (!wy_last) begin
                                    wy <= wy + 1'b1;
                                end else begin
                                    wy <= {WIN_W{1'b0}};
                                    if (!g_last) begin
                                        g        <= g + 1'b1;
                                        w_base_g <= group_base(g + 1'b1, t_ext, cfg_wbase);
                                    end else begin
                                        state <= S_IDLE;
                                    end
                                end
                            end
                        end
                    end else begin
                        t <= t_after;
                        c <= two ? c2 : c1;
                        i <= two ? i2 : i1;
                        j <= two ? j2 : j1;
                    end
                end

                default: state <= S_IDLE;
            endcase
        end
    end

    // ---- operand pipeline -------------------------------------------------------------
    // Stage A: address registers.  Stage B: RAM outputs are valid.  Stages C and D: adder tree.
    localparam PIPE = 5;
    reg [1:0] slot_v_p [0:PIPE-1];
    reg [1:0] slot_l_p [0:PIPE-1];
    reg       pass_p   [0:PIPE-1];
    reg [1:0] pad_b;

    wire last0 = advance & unit_end & ~two;
    wire last1 = advance & unit_end & two;

    wire [7:0] a0_b = pad_b[0] ? 8'd0 : act_data0;
    wire [7:0] a1_b = pad_b[1] ? 8'd0 : act_data1;

    // Stage B2: RAM outputs registered, so BRAM clock-to-out does not eat into the adder tree.
    reg [7:0]       a0_r, a1_r;
    reg [K*W_W-1:0] w0_r, w1_r;

    reg [7:0]       a0_c, a0_d, a1_c, a1_d;
    reg [K*W_W-1:0] w0_c, w0_d, w1_c, w1_d;

    wire [WC1_W-1:0] wc1_0, wc1_1;
    wire [WC2_W-1:0] wc2_0, wc2_1;
    wire [WC3_W-1:0] wc3_0, wc3_1;

    wc_gen #(.K(K), .C3_EN(C3_EN), .W_W(W_W), .WC1_W(WC1_W), .WC2_W(WC2_W), .WC3_W(WC3_W)) u_wc0 (
        .clk(clk), .w(w0_r), .wc1(wc1_0), .wc2(wc2_0), .wc3(wc3_0));

    integer p;
    always @(posedge clk) begin
        if (rst) begin
            for (p = 0; p < PIPE; p = p + 1) begin
                slot_v_p[p] <= 2'b00;
                slot_l_p[p] <= 2'b00;
                pass_p[p]   <= 1'b0;
            end
        end else begin
            slot_v_p[0] <= {advance & two, advance};
            slot_l_p[0] <= {last1, last0};
            pass_p[0]   <= advance & pass_first;
            for (p = 1; p < PIPE; p = p + 1) begin
                slot_v_p[p] <= slot_v_p[p-1];
                slot_l_p[p] <= slot_l_p[p-1];
                pass_p[p]   <= pass_p[p-1];
            end
        end
        pad_b <= pad_a;
        a0_r  <= a0_b;
        w0_r  <= w_data0;
        a1_r  <= a1_b;
        w1_r  <= w_data1;
        a0_c  <= a0_r;
        a0_d  <= a0_c;
        w0_c  <= w0_r;
        w0_d  <= w0_c;
        a1_c  <= a1_r;
        a1_d  <= a1_c;
        w1_c  <= w1_r;
        w1_d  <= w1_c;
    end

    assign fifo_wr = slot_v_p[PIPE-1][0];

    wire [SLOT_W-1:0] slot0;
    wire [SLOT_W-1:0] slot1;

    generate
        if (C3_EN != 0) begin : set_c3
            assign slot0 = {slot_v_p[PIPE-1][0], pass_p[PIPE-1], slot_l_p[PIPE-1][0], a0_d, w0_d, wc3_0, wc2_0, wc1_0};
            assign slot1 = {slot_v_p[PIPE-1][1], 1'b0,           slot_l_p[PIPE-1][1], a1_d, w1_d, wc3_1, wc2_1, wc1_1};
        end else begin : set_no_c3
            assign slot0 = {slot_v_p[PIPE-1][0], pass_p[PIPE-1], slot_l_p[PIPE-1][0], a0_d, w0_d, wc2_0, wc1_0};
            assign slot1 = {slot_v_p[PIPE-1][1], 1'b0,           slot_l_p[PIPE-1][1], a1_d, w1_d, wc2_1, wc1_1};
            wire unused_wc3 = &{1'b0, wc3_0, wc3_1};
        end

        if (R == 2) begin : two_slots
            wc_gen #(.K(K), .C3_EN(C3_EN), .W_W(W_W), .WC1_W(WC1_W), .WC2_W(WC2_W), .WC3_W(WC3_W)) u_wc1 (
                .clk(clk), .w(w1_r), .wc1(wc1_1), .wc2(wc2_1), .wc3(wc3_1));
            assign fifo_data = {slot1, slot0};
        end else begin : one_slot
            assign wc1_1 = {WC1_W{1'b0}};
            assign wc2_1 = {WC2_W{1'b0}};
            assign wc3_1 = {WC3_W{1'b0}};
            assign fifo_data = slot0;
            wire unused_slot1 = &{1'b0, slot1};
        end
    endgenerate

    wire unused_cfg = &{1'b0, pass_end, cfg_g[15:G_W], t[15:ACT_AW], cfg_t[15:MW]};
endmodule

`default_nettype wire
