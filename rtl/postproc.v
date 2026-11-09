`timescale 1ns / 1ps
`default_nettype none

// Post-processing of one lane result (SPEC 3.3):
//   v = acc + b;  q = (v*M + 2^(n-1)) >> n  (no rounding term when n = 0);  y = clamp(q, 0, 255).
// Latency: 1 cycle to v (used directly for FC), 4 cycles to y.  SB is carried unchanged.
module postproc #(
    parameter ACC_W  = 32,
    parameter V_W    = 33,
    parameter PROD_W = 50,
    parameter SB_W   = 16
) (
    input  wire              clk,
    input  wire              rst,
    input  wire              in_valid,
    input  wire [ACC_W-1:0]  y,
    input  wire [31:0]       b,
    input  wire [15:0]       m,
    input  wire [4:0]        n,
    input  wire [SB_W-1:0]   in_sb,
    output reg               v_valid,
    output reg  signed [V_W-1:0] v,
    output reg  [SB_W-1:0]   v_sb,
    output reg               out_valid,
    output reg  [7:0]        out,
    output reg  [SB_W-1:0]   out_sb,
    output wire              busy
);
    wire signed [V_W-1:0] y_ext = {{(V_W-ACC_W){y[ACC_W-1]}}, y};
    wire signed [V_W-1:0] b_ext = {{(V_W-32){b[31]}}, b};

    reg                      valid2, valid3;
    reg [SB_W-1:0]           sb2, sb3;
    reg signed [PROD_W-1:0]  prod;
    reg signed [PROD_W-1:0]  shifted;

    wire signed [PROD_W-1:0] round_term = (n == 5'd0) ? {PROD_W{1'b0}} : ({{(PROD_W-1){1'b0}}, 1'b1} << (n - 1'b1));
    wire signed [16:0]       m_ext = {1'b0, m};
    wire signed [V_W+16:0]   full_product = v * m_ext;
    wire signed [PROD_W-1:0] rounded = prod + round_term;

    wire        negative = shifted[PROD_W-1];
    wire        overflow = |shifted[PROD_W-2:8];

    assign busy = in_valid | v_valid | valid2 | valid3;

    always @(posedge clk) begin
        v    <= y_ext + b_ext;
        v_sb <= in_sb;
        prod <= full_product[PROD_W-1:0];
        sb2  <= v_sb;
        shifted <= rounded >>> n;
        sb3  <= sb2;
        out  <= negative ? 8'd0 : (overflow ? 8'd255 : shifted[7:0]);
        out_sb <= sb3;
        if (rst) begin
            v_valid   <= 1'b0;
            valid2    <= 1'b0;
            valid3    <= 1'b0;
            out_valid <= 1'b0;
        end else begin
            v_valid   <= in_valid;
            valid2    <= v_valid;
            valid3    <= valid2;
            out_valid <= valid3;
        end
    end

    wire unused_full = &{1'b0, full_product};
endmodule

`default_nettype wire
