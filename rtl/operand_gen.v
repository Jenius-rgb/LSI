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
//
// ZERO_SKIP != 0 (ADR-028): a set whose activation is 0 is not sent, unless it closes a unit (last) or opens a pass
// (pass_start). Every product of such a set is 0 in every data and checksum lane, so all sums are unchanged. Kept sets
// are packed into slot 0 first, so the fast side still sees a valid slot 0 in every word, and a word with no kept
// set is not written.
// ZERO_SKIP = 1 also keeps at least MINW = K + 2 + C3 sets per unit (zero sets near the unit end are kept when
// needed): the lane-array result serializer sends MINW words per unit, one per cycle, so units must not end closer
// than that. ZERO_SKIP = 2 drops every zero set and leaves the spacing to a stall in fast_path.
module operand_gen #(
    parameter K         = 8,
    parameter ZERO_SKIP = 0,
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

    localparam [2:0] S_IDLE = 3'd0, S_RUN = 3'd1, S_LOG_ADDR = 3'd2, S_LOG_DATA = 3'd3, S_LOG_NEXT = 3'd4, S_LOG_BASE = 3'd5;
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

    // Values derived from the layer configuration are static during a pass: registered,
    // so loop control only compares registers.
    reg [15:0]      t_last_r, t_last2_r;
    reg [WIN_W-1:0] win_max_r;
    reg [G_W-1:0]   g_max_r;
    reg             t_zero;

    always @(posedge clk) begin
        t_last_r  <= cfg_t - 16'd1;
        t_last2_r <= cfg_t - 16'd2;
        win_max_r <= cfg_is_fc ? {WIN_W{1'b0}} : (({{(WIN_W-1){1'b0}}, 1'b1} << (cfg_log2w - 1'b1)) - 1'b1);
        g_max_r   <= cfg_g[G_W-1:0] - 1'b1;
    end

    wire        two      = (R == 2) && (t != t_last_r);
    wire [15:0] t_after  = t + (two ? 16'd2 : 16'd1);
    wire        unit_end = two ? (t == t_last2_r) : ((R == 2) | (t == t_last_r));

    // ---- loop exits -------------------------------------------------------------------
    wire pos_last   = cfg_is_fc ? 1'b1 : (pos == 2'd3);
    wire wx_last    = (wx == win_max_r);
    wire wy_last    = (wy == win_max_r);
    wire g_last     = (g == g_max_r);
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
    wire new_unit = t_zero;
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
            t_zero     <= 1'b1;
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
                    t_zero     <= 1'b1;
                    state      <= use_log ? S_LOG_ADDR : S_RUN;
                end

                S_LOG_ADDR: state <= S_LOG_DATA;

                S_LOG_DATA: begin
                    g     <= log_g;
                    wy    <= log_wy;
                    wx    <= log_wx;
                    pos   <= 2'd0;
                    state <= S_LOG_BASE;
                end

                S_LOG_BASE: begin
                    w_base_g <= group_base(g, t_ext, cfg_wbase);
                    state    <= S_RUN;
                end

                S_LOG_NEXT: begin
                    log_addr <= log_addr + 1'b1;
                    if ({1'b0, log_addr} + 1'b1 == log_count) state <= S_IDLE;
                    else state <= S_LOG_ADDR;
                end

                S_RUN: if (advance) begin
                    pass_first <= 1'b0;
                    t_zero     <= unit_end;
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
                                        w_base_g <= w_base_g + cfg_t[WEIGHT_AW-1:0];
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

    // Zero skipping at the FIFO write (ADR-028).
    wire zs    = (ZERO_SKIP != 0);
    wire drop0 = (a0_d == 8'd0) & ~slot_l_p[PIPE-1][0] & ~pass_p[PIPE-1];
    wire drop1 = (a1_d == 8'd0) & ~slot_l_p[PIPE-1][1];
    wire room0, room1;                        // dropping still leaves room for MINW sets in the unit
    wire keep0  = slot_v_p[PIPE-1][0] & ~(zs & drop0 & room0);
    wire keep1  = slot_v_p[PIPE-1][1] & ~(zs & drop1 & room1);
    // Gated by zs so that ZERO_SKIP = 0 synthesizes the original slot wiring: synthesis cannot prove that a valid
    // slot 1 implies a valid slot 0, and the ungated mux cost 118 LUTs in the baseline (official run, 26 Nov 2026).
    wire shift1 = zs & ~keep0 & keep1;        // set 1 moves into slot 0

    generate
        if (ZERO_SKIP == 1) begin : min_sets
            // need = MINW - (sets after this one in the unit), floored at 0: a zero set may be dropped only while
            // the sets already kept reach it, because the rest of the unit can then still bring the count to MINW.
            localparam integer MINW = K + 2 + (C3_EN != 0 ? 1 : 0);
            localparam integer NW   = $clog2(MINW + 2);
            localparam integer MINW1 = MINW + 1;
            localparam [NW-1:0] MINW_N = MINW[NW-1:0];
            reg  [NW-1:0] need0_p [0:PIPE-1];
            reg  [NW-1:0] need1_p [0:PIPE-1];
            reg  [NW-1:0] kept;               // sets kept so far in the current unit, saturating at MINW
            wire [15:0]   after0 = t_last_r - t;          // sets after set 0 (set 1 is one closer to the end)
            wire [NW-1:0] need0  = (after0 >= MINW[15:0]) ? {NW{1'b0}} : MINW_N - after0[NW-1:0];
            wire [NW-1:0] need1  = (after0 >= MINW1[15:0]) ? {NW{1'b0}} : MINW_N + 1'b1 - after0[NW-1:0];
            wire [NW-1:0] need0_d = need0_p[PIPE-1];
            wire [NW-1:0] need1_d = need1_p[PIPE-1];
            wire [NW-1:0] kept_mid = (keep0 && kept != MINW_N) ? kept + 1'b1 : kept;
            assign room0 = (kept >= need0_d);
            // kept_mid depends on keep0; both outcomes are compared in parallel.
            assign room1 = keep0 ? ((kept != MINW_N ? kept + 1'b1 : kept) >= need1_d) : (kept >= need1_d);
            integer q;
            always @(posedge clk) begin
                need0_p[0] <= need0;
                need1_p[0] <= need1;
                for (q = 1; q < PIPE; q = q + 1) begin
                    need0_p[q] <= need0_p[q-1];
                    need1_p[q] <= need1_p[q-1];
                end
                if (rst | (|slot_l_p[PIPE-1]))
                    kept <= {NW{1'b0}};      // the unit ends in this word (a word never spans two units)
                else if (keep1 && kept_mid != MINW_N)
                    kept <= kept_mid + 1'b1;
                else
                    kept <= kept_mid;
            end
        end else begin : no_min_sets
            assign room0 = 1'b1;
            assign room1 = 1'b1;
        end
    endgenerate

    assign fifo_wr = zs ? (keep0 | keep1) : keep0;

    wire [SLOT_W-1:0] slot0;
    wire [SLOT_W-1:0] slot1;
    wire [SLOT_W-1:0] set0;
    wire [SLOT_W-1:0] set1;

    generate
        if (C3_EN != 0) begin : set_c3
            assign set0  = {keep0, pass_p[PIPE-1], slot_l_p[PIPE-1][0], a0_d, w0_d, wc3_0, wc2_0, wc1_0};
            assign set1  = {keep1, 1'b0,           slot_l_p[PIPE-1][1], a1_d, w1_d, wc3_1, wc2_1, wc1_1};
        end else begin : set_no_c3
            assign set0  = {keep0, pass_p[PIPE-1], slot_l_p[PIPE-1][0], a0_d, w0_d, wc2_0, wc1_0};
            assign set1  = {keep1, 1'b0,           slot_l_p[PIPE-1][1], a1_d, w1_d, wc2_1, wc1_1};
            wire unused_wc3 = &{1'b0, wc3_0, wc3_1};
        end

        assign slot0 = shift1 ? set1 : set0;
        assign slot1 = shift1 ? {1'b0, set1[SLOT_W-2:0]} : set1;

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
