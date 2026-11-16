`timescale 1ns / 1ps
`default_nettype none

// XADC on the Spartan-7 (ADR-023, UG480 v1.11).  Only used under Vivado.
//   INIT_40 = 0000h  no averaging on the selected channels; calibration averaging on (Table 3-4)
//   INIT_41 = 20F0h  continuous sequence mode (SEQ = 0010, Table 3-9); calibration corrections
//                    CAL0-CAL3 on (DI4-DI7, Table 3-5); alarm outputs left enabled and unconnected
//   INIT_42 = 0800h  DCLK / 8: 125 MHz gives ADCCLK = 15.625 MHz, inside 1-26 MHz (Table 3-12;
//                    DS189 Table 50)
//   INIT_48 = 0101h  sequence = calibration (bit 0) and on-chip temperature (bit 8) (Table 4-1)
// The temperature result is status register 00h, MSB justified (Table 3-1).
module xadc_prim_xilinx (
    input  wire        dclk,
    input  wire        reset,
    input  wire        den,
    input  wire [6:0]  daddr,
    output wire [15:0] dout,
    output wire        drdy
);
    XADC #(
        .INIT_40(16'h0000), .INIT_41(16'h20F0), .INIT_42(16'h0800),
        .INIT_48(16'h0101), .INIT_49(16'h0000), .INIT_4A(16'h0000), .INIT_4B(16'h0000)
    ) u_xadc (
        .DCLK(dclk), .RESET(reset), .DEN(den), .DADDR(daddr), .DWE(1'b0), .DI(16'h0000),
        .DO(dout), .DRDY(drdy), .CONVST(1'b0), .CONVSTCLK(1'b0),
        .VP(), .VN(), .VAUXP(), .VAUXN(),
        .ALM(), .OT(), .BUSY(), .CHANNEL(), .EOC(), .EOS(), .JTAGBUSY(), .JTAGLOCKED(), .JTAGMODIFIED(), .MUXADDR());
endmodule

`default_nettype wire
