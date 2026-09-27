`timescale 1ns / 1ps
/*
    core of TimeTagger, an OpalKelly based single photon counting library
    Copyright (C) 2011  Markus Wick <wickmarkus@web.de>

    This program is free software; you can redistribute it and/or modify
    it under the terms of the GNU General Public License as published by
    the Free Software Foundation; either version 2 of the License, or
    (at your option) any later version.

    This program is distributed in the hope that it will be useful,
    but WITHOUT ANY WARRANTY; without even the implied warranty of
    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
    GNU General Public License for more details.

    You should have received a copy of the GNU General Public License along
    with this program; if not, write to the Free Software Foundation, Inc.,
    51 Franklin Street, Fifth Floor, Boston, MA 02110-1301 USA.
*/
//////////////////////////////////////////////////////////////////////////////////
// top module of hte TimeTagger
// it connects three modules:
// Tagger->Buffer->OpalKelly
//////////////////////////////////////////////////////////////////////////////////
module TimeTaggerController #(parameter CHANNELS=16)(
	input	 wire 							clk,		// tagger base clock
	input	 wire [(CHANNELS/2)-1:0]	trig,		// input line

	// Opal-Kelly Host Interface - USB chip connection
	input	 wire [7:0]						hi_in,
	output wire [1:0]						hi_out,
	inout	 wire [15:0]					hi_inout,
	output wire								hi_muxsel,
	output wire								i2c_sda,
	output wire								i2c_scl,
	output wire  [3:0]					led,
	output wire								trig_out,
	//outputs for signal copy
	output wire [2:0]							sig_copy,
	
	// SRAM connectors
	input  wire								sdram_clk,
	output wire [3:0]  					sdram_cmd,		
	output wire [1:0]  					sdram_ba,
	output wire [12:0] 					sdram_a,
	inout  wire [15:0] 					sdram_d,
	output wire 							sdram_ldqm,
	output wire								sdram_udqm,
	output wire								sdram_cke
	
);

assign trig_out = trig[0] | trig[1];	// Inclusive OR to "sum up" the two APD's
assign sig_copy[0] = trig[0];				// Copy of Channel 0
// assign sig_copy[1] = trig[2];				// AOM Out, not needed anymore due to "fuse"
// assign sig_copy[2] = trig[4];				// Copy of Channel 4
assign sig_copy[2] = trig[5];				// Copy of Channel 5 (pixeltrigger)

wire pulse;
PulsTester test_generator (
    .pulse(pulse), 
    .clk_input(clk)
);

//////////////////
// global wires //
//////////////////

wire 			tagger_enable;
wire [31:0]	tagger_data;

wire 			buffer_full;
wire			buffer_empty;
reg  [15:0]	buffer_dout;

wire			ok_clk;
wire			ok_read_enable;
wire [15:0] ok_empty_thresh;
wire [15:0] ok_enable_channel;
wire			protector_reset;

////////////////
// TimeTagger //
////////////////

TimeTagger #(.CHANNELS(CHANNELS)) tagger (
   .trig_clk(clk), 
   .trig_line({pulse,trig[6:0]}), 
   .write_full(buffer_full), 
   .write_enable(tagger_enable), 
   .write_data(tagger_data), 
   .conf_enable_channel(ok_enable_channel)
);

////////////
// Buffer //
////////////
wire [15:0] buffer_slow_data;
wire			buffer_slow_empty;
wire			buffer_out_full;
wire			buffer_out_empty;
wire [15:0] buffer_out_data;
reg 			buffer_send_empty;
reg			buffer_clear_output;

/*

// small buffer in both clk domain, and convert 32bit to 16bit
OutputBufferSmall output_buffer_small (
  .wr_clk(clk), // input wr_clk
  .rd_clk(ok_clk), // input rd_clk
  .din(tagger_data), // input [31 : 0] din
  .wr_en(tagger_enable), // input wr_en
  .rd_en(!buffer_out_full && !buffer_slow_empty), // input rd_en
  .dout(buffer_slow_data), // output [15 : 0] dout
  .full(), // output full
  .almost_full(buffer_full), // output almost_full
  .empty(buffer_slow_empty) // output empty
);

// big buffer in slow usb clk domain
OutputBuffer output_buffer (
  .clk(ok_clk), // input clk
  .din(buffer_slow_data), // input [15 : 0] din
  .wr_en(!buffer_out_full && !buffer_slow_empty), // input wr_en
  .rd_en(ok_read_enable && !buffer_out_empty && !buffer_send_empty), // input rd_en
  .prog_empty_thresh(ok_empty_thresh), // input [13 : 0] prog_empty_thresh
  .dout(buffer_out_data), // output [15 : 0] dout
  .full(buffer_out_full), // output full
  .almost_full(), // output almost_full
  .empty(buffer_out_empty), // output empty
  .prog_empty(buffer_empty) // output prog_empty
);

assign sdram_cmd = 0;
assign sdram_ba = 0;
assign sdram_a = 0;
assign led = 0;
*/

assign sdram_cke = 1'b1;
assign sdram_ldqm = 1'b0;
assign sdram_udqm = 1'b0;

RamFifo output_buffer (
    .wr_clk(clk), 
    .ram_clk(sdram_clk), 
    .rd_clk(ok_clk), 
    .din(tagger_data), 
    .wr_en(tagger_enable), 
    .rd_en(ok_read_enable && !buffer_out_empty && !buffer_send_empty), 
    .prog_empty_thresh(ok_empty_thresh), 
    .dout(buffer_out_data), 
    .full(), 
    .almost_full(buffer_full), 
    .empty(buffer_out_empty), 
    .prog_empty(buffer_empty), 
    .sdram_cmd(sdram_cmd), 
    .sdram_ba(sdram_ba), 
    .sdram_a(sdram_a), 
    .sdram_d(sdram_d),
	 .led(led)
    );


// if empty, send zeros
always @(*) begin
	if(buffer_clear_output)
		buffer_dout <= 16'h0000;
	else
		buffer_dout <= buffer_out_data;
end

// to be sure, that only multiples of two counts of zeros are send
always @(posedge ok_clk) begin
	if(buffer_send_empty) begin
		buffer_send_empty <= !ok_read_enable;
		buffer_clear_output <= 1;
	end else begin
		buffer_send_empty <= ok_read_enable && buffer_out_empty;
		buffer_clear_output <= ok_read_enable && buffer_out_empty;
	end
end

/////////////////////
// Opal Kelly Host //
/////////////////////
assign hi_muxsel = 1'b0;
assign i2c_sda = 1'bz;
assign i2c_scl = 1'bz;

// Opal Kelly Host Interface internal connections
parameter N = 1; // count of connectors to ok2x
wire [30:0]			ok1;
wire [16:0]			ok2;
wire [17*N-1:0]	ok2x;

// Opal Kelly Host
okHost okHI	(
	.hi_in( hi_in ),
	.hi_out( hi_out ),
	.hi_inout( hi_inout ),
	.ti_clk( ok_clk ),
	.ok1( ok1 ),
	.ok2( ok2 )
);

// Opal Kelly output multiplexer
okWireOR #(.N(N)) okOr ( ok2, ok2x );        // N = 3: 1 x okBTPipeOut pipe, 2 x okWireOut

// Opal Kelly block throttled output pipe
okBTPipeOut okPipe ( 	
	.ok1( ok1 ),
	.ok2( ok2x[ 0*17 +: 17 ] ),
	.ep_addr( 8'ha0 ),
	.ep_datain( buffer_dout ),         // get data from fifo
	.ep_read( ok_read_enable ),          // request data
	.ep_blockstrobe( ),
	.ep_ready( !buffer_empty )        // fifo initalizes data transmission
);

// fifo controllable full threshold
okWireIn ep01 (
	.ok1(ok1), 
	.ep_addr(8'h01),
	.ep_dataout( ok_empty_thresh )
);

// fifo controllable full thresshold
okWireIn ep02 (
	.ok1(ok1), 
	.ep_addr(8'h02),
	.ep_dataout( ok_enable_channel )
);

okWireIn ProtectorResetWire (
	.ok1( ok1 ),										// host interface
	.ep_addr( 8'h0F ),									// endpoint address 8'h03
	.ep_dataout( protector_reset )		// force laser on
);
                            
//Instantiate an APD protection module
ApdProtection protector ( 
	.photon (trig_out), 			// Sum of the two APD's
	.laser (trig[2]),				// Laser Pulse from Pulser
//	.reset (protector_reset),	// ResetSwitch
	.clk (clk),						
	.aomout (sig_copy[1])		// AOM Out
);

			
endmodule
