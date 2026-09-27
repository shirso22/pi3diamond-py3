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
// dummy filter, do nearly nothing
// except one: deadtime of one clock period
//////////////////////////////////////////////////////////////////////////////////
module TaggerFilter#(parameter CHANNELS=1, parameter BITS=1) (
    input  wire							clk,
	 
    input  wire [BITS*CHANNELS-1:0] in_subtimes,
	 input  wire [CHANNELS-1:0] 		in_edge_detected,
	 
    output reg  [BITS*CHANNELS-1:0] out_subtimes,
	 output reg  [CHANNELS-1:0] 		out_edge_detected,
	 
	 input  wire [CHANNELS-1:0] 		enable_channel
);

// dead time
reg  [BITS*CHANNELS-1:0] 	dead_subtimes;
reg  [CHANNELS-1:0] 			dead_edge_detected;

reg  [BITS*CHANNELS-1:0] 	dead_subtimes2;
reg  [CHANNELS-1:0] 			dead_edge_detected2;
reg  [CHANNELS-1:0] 			dead_edge_detected3;
reg  [CHANNELS-1:0]			dead_newer;

// channel activated
reg  [BITS*CHANNELS-1:0] 	channel_subtimes;
reg  [CHANNELS-1:0] 			channel_edge_detected;

// laster filter
reg photon_seen;


initial begin
	out_edge_detected <= 0;
	dead_edge_detected <= 0;
	channel_edge_detected <= 0;
	photon_seen <= 0;
end

always @(posedge clk) begin

	
   // dead time
	dead_subtimes       <= in_subtimes;
	dead_edge_detected  <= in_edge_detected;
	
	dead_subtimes2      <= dead_subtimes;
	dead_edge_detected2 <= dead_edge_detected & (~dead_edge_detected3 | dead_newer);
	dead_edge_detected3 <= dead_edge_detected;
end


genvar i;
generate
for(i=0; i<CHANNELS; i=i+1) begin: dead
	always @(posedge clk) begin
		dead_newer[i] <= dead_subtimes[BITS*(i+1)-1:BITS*i] < in_subtimes[BITS*(i+1)-1:BITS*i];
	end
end
endgenerate
	

always @(posedge clk) begin
	// channel activated
	channel_subtimes <= dead_subtimes2;
	channel_edge_detected <= dead_edge_detected2 & enable_channel[CHANNELS-1:0];
	
	// laser filter
	photon_seen <= (photon_seen && !channel_edge_detected[4]) || channel_edge_detected[0];
	out_subtimes <= channel_subtimes;
	out_edge_detected <= channel_edge_detected;	
	out_edge_detected[4] <= channel_edge_detected[4] && photon_seen;

end

endmodule
