`timescale 1ns / 1ps
`default_nettype none

// Hardware governor (SPEC 10), identical in state trajectory to model/governor.py.
// image_done triggers one update using the per-layer failure mask and the correction total
// collected by the engine during the image.  Layers update one per cycle.
module governor #(
    parameter LAYERS = 8
) (
    input  wire              clk,
    input  wire              rst,
    input  wire              init,
    input  wire              auto_mode,
    input  wire [7:0]        n_up,
    input  wire [7:0]        cooldown,
    input  wire [15:0]       corr_hi,
    input  wire [3:0]        l_min,
    input  wire [3:0]        l_max,

    input  wire              image_done,
    input  wire [LAYERS-1:0] fail_mask,
    input  wire [15:0]       corr_total,

    output reg  [3:0]        level,
    output reg  [LAYERS-1:0] turbo_en,
    output reg  [7:0]        clean_streak,
    output wire              busy,
    output reg               level_changed
);
    localparam integer IDX_W = $clog2(LAYERS);

    reg [7:0] cool [0:LAYERS-1];
    reg [IDX_W:0] idx;
    reg       running;
    reg       any_fail;

    assign busy = running;

    integer l;
    wire [IDX_W-1:0] i = idx[IDX_W-1:0];

    wire [7:0] cool_after = (cool[i] > 8'd0) ? cool[i] - 8'd1 : 8'd0;

    wire slow_down = any_fail | fail_mask[i] | (corr_total > corr_hi);

    always @(posedge clk) begin
        level_changed <= 1'b0;
        if (rst | init) begin
            level        <= l_min;
            turbo_en     <= {LAYERS{1'b1}};
            clean_streak <= 8'd0;
            running      <= 1'b0;
            idx          <= {(IDX_W+1){1'b0}};
            any_fail     <= 1'b0;
            for (l = 0; l < LAYERS; l = l + 1) cool[l] <= 8'd0;
        end else if (running) begin
            // Layer by layer, as in the loop of SPEC 10.
            if (fail_mask[i]) begin
                turbo_en[i] <= 1'b0;
                cool[i]     <= cooldown;
                any_fail    <= 1'b1;
            end else if (!turbo_en[i]) begin
                cool[i] <= cool_after;
                if (cool_after == 8'd0) turbo_en[i] <= 1'b1;
            end

            if (idx == LAYERS[IDX_W:0] - 1'b1) begin
                running <= 1'b0;
                if (slow_down) begin
                    if (level > l_min) begin
                        level         <= level - 1'b1;
                        level_changed <= 1'b1;
                    end
                    clean_streak <= 8'd0;
                end else if (clean_streak + 1'b1 >= n_up) begin
                    if (level < l_max) begin
                        level         <= level + 1'b1;
                        level_changed <= 1'b1;
                    end
                    clean_streak <= 8'd0;
                end else begin
                    clean_streak <= clean_streak + 1'b1;
                end
            end else begin
                idx <= idx + 1'b1;
            end
        end else if (image_done && auto_mode) begin
            running  <= 1'b1;
            idx      <= {(IDX_W+1){1'b0}};
            any_fail <= 1'b0;
        end
    end
endmodule

`default_nettype wire
