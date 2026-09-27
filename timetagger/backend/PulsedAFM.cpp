/*
    backend for TimeTagger, an OpalKelly based single photon counting library
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
// PY3-PORT: boost_thread 1.47 replaced with the C++11 standard library.
// boost/thread.hpp also pulled in <cassert> and <map> transitively;
// the standard headers do not, so they are declared explicitly.
#include <cassert>
#include <map>
#include <vector>
#include <string>
#include <cstring>
#include <mutex>
#include <thread>
#include <chrono>

#include <fstream>
#include <iostream>
#include <list>

#include "TimeTagger.h"

using namespace std;

struct _PulsedAFMEdge {
	long long edge;
	int pulse;
};

class PulsedAFM : public _Iterator {
public:
	PulsedAFM(int _length, long long _binwidth, int _sequence_length, int _channel_0, int _channel_1, int _pixel_count=256, 
		int _line_count=256, int _win_low=300, int _win_high=400, int _refwin_low=800, int _refwin_high=900, int _shot_trigger=-1, int _sequence_trigger=-1, int _pixel_trigger=-1, int _line_trigger=-1) {
		channel_0 = _channel_0;
		channel_1 = _channel_1;

		shot_trigger = _shot_trigger;
		sequence_trigger = _sequence_trigger;
		pixel_trigger = _pixel_trigger;
		line_trigger = _line_trigger;

		sequence_length = _sequence_length;

		length = _length;
		binwidth = _binwidth;
		pixel_count = _pixel_count;
		line_count = _line_count;

		/*
		cout << "C++: pixel_count" << endl;
		cout << pixel_count << endl;
		cout << "C++: line_count" << endl;
		cout << line_count << endl;
		cout << "C++: sequence_length" << endl;
		cout << sequence_length << endl;
		*/

		datalength = pixel_count*line_count*sequence_length*2;

		/*
		cout << "datalength" << endl;
		cout << datalength << endl;
		*/

		win_low = _win_low;
		win_high = _win_high;
		refwin_low = _refwin_low;
		refwin_high = _refwin_high;

		if(channel_0>=0)
			registerChannel(channel_0);
		if(channel_1>=0)
			registerChannel(channel_1);
		if(shot_trigger>=0)
			registerChannel(shot_trigger);
		if(sequence_trigger>=0)
			registerChannel(sequence_trigger);
		if(pixel_trigger>=0)
			registerChannel(pixel_trigger);
		if(line_trigger>=0)
			registerChannel(line_trigger);

		cout << "C++: initializing data" << endl;
		try
		{
			data = new int[datalength];
			if(!data)
				cout << "C++: Warning: Konnte Speicher nicht allocieren" << endl;
		}
		catch (const std::exception &exc)
		{
			cout << "C++: Error in new int[]" << endl;
			cout << exc.what() << endl;
		}
		cout << "C++: clearing data" << endl;
		clear();
		cout << "C++: Starting TimeTagger" << endl;
		start();
	}

	virtual ~PulsedAFM() {
		stop();
		if(data)
			delete [] data;
	}
	
	virtual void start() {
		lock();
		waiting_for_sync = (sequence_trigger>=0) ? 1 : 0;
		pulse = -1;
		unlock();
		
		_Iterator::start();
		
	}

	void getData(float **ARGOUTVIEWM_ARRAY3, int *DIM1, int *DIM2, int *DIM3) {
		if(!data) {ARGOUTVIEWM_ARRAY3 = 0; DIM1 = 0; DIM2 = 0; DIM3 = 0; return;}
		
		float *arr = new float[sequence_length*2*pixel_count*line_count];
		if(!arr) {
			ARGOUTVIEWM_ARRAY3 = 0; DIM1 = 0; DIM2 = 0; DIM3 = 0;
			cout << "Warning: Konnte Speicher nicht allocieren f�r arr" << endl;
			return;}
		
		for (int i=0; i<sequence_length*2*pixel_count*line_count; i++){
			arr[i]=0;
		}
		
		lock();
		int i=0;
		for ( int iy=0; iy<line_count; iy++) {
			for ( int ix=0; ix<pixel_count; ix++){
				for ( int j=0; j<sequence_length; j++){
					float win = 0.0;
					float refwin = 0.0;
					win += data[iy*pixel_count*2*sequence_length+ix*2*sequence_length+j*2+0];
					refwin += data[iy*pixel_count*2*sequence_length+ix*2*sequence_length+j*2+1];
					if (win!=0.0 && refwin!=0.0){
						arr[i]=win/(win_high-win_low); // normalized so different window sizes do not matter
						arr[i+1]=refwin/(refwin_high-refwin_low); // normalized so different window sizes do not matter
						// multiplied by 1000000 to be able to use integer, division
						// arr[i]=int(1000000*(win/(win_high-win_low)-(refwin/(refwin_high-refwin_low)))); // multiplied by 1000000 to be able to use integer, substraction
					}
					i = i+2;
				}
			}
		}

		*ARGOUTVIEWM_ARRAY3 = arr;
		*DIM1 = line_count;
		*DIM2 = pixel_count;
		*DIM3 = sequence_length*2;
		//*DIM3 = sequence_length;
		
		unlock();
	}

	int getCounts() {
		return counts;
	}

	virtual void clear() {
		lock();
		for(int i=0; i<datalength; i++) {
			data[i] = 0;
		}
		waiting_for_sync = (sequence_trigger>=0) ? 1 : 0;
		pulse = -1;
		counts = 0;
		x = 0;
		// we set the negative line in y, since at the start of the scan a linetrigger is always given
		y = -1;

		// we set backward to 1 since the first linetrigger is given before we start with a forward scan 
		backward = 1;

		edge.clear();

		unlock();
	}
protected:

	virtual void next(Tag* list, int count, long long time) {
		for(int i = 0; i < count; i++) {
			Tag t = list[i];
			
			// on overflow
			if(t.overflow) {
				pulse = -1;
				waiting_for_sync = (sequence_trigger>=0) ? 1 : 0;
				edge.clear();
			}

			// pixel and line trigger handling
			if(t.chan == line_trigger) {
				// Only switch line after backward scan.
				if(backward == 1) {
					waiting_for_sync = (sequence_trigger>=0) ? 1 : 0;
					if(y<line_count-1) {
						y++;
						x=-1;
					}
					cout << "C++: line triggered. Moved to next line." << endl;
				} else {
					cout << "C++: line triggered. But the joke's on you, I didn't do anything!" << endl;
				}
				// Switch between forward and backward
				if(backward == 1) {
					backward = 0;
				} else {
					if(backward == 0) {
						backward = 1;
					}
				}
			}

			if(t.chan == pixel_trigger){
				waiting_for_sync = (sequence_trigger>=0) ? 1 : 0;
				if(x<pixel_count-1) x++;
				//cout << "pixel triggered" << endl;
			}

			// on sync
			if(t.chan == sequence_trigger) {
				pulse = -1;
				waiting_for_sync = 0;
				counts++;
			}

			// on laser, increase pulse and set edge
			if(t.chan == shot_trigger && !waiting_for_sync && x>=0 && y>=0) {
				pulse++;
				
				if(pulse >= sequence_length) {
					if(sequence_trigger>=0) {
						waiting_for_sync = 1;
					} else {
						pulse = 0;
						counts++;
					}
				}
				if(pulse < sequence_length && pulse >= 0) {
					_PulsedAFMEdge e;
					e.edge = t.time;
					e.pulse = pulse;
					assert(pulse >= 0 && pulse < sequence_length);
					edge.push_back(e);
				}
				if(!edge.empty() && t.time - edge.front().edge > length*binwidth)
					edge.pop_front();
			}

			// on photon in histogram range
			if((t.chan == channel_0 || t.chan == channel_1) && !waiting_for_sync) {
				std::list<_PulsedAFMEdge>::iterator it;
				
				for(it = edge.begin(); it != edge.end(); it++) {
					if( (t.time - (it->edge))/binwidth < length && (t.time - (it->edge))/binwidth >= 0) {
						assert(it->pulse < sequence_length);
						assert(it->pulse >= 0);

						assert(it->pulse*length + (t.time-(it->edge))/binwidth < sequence_length*length);
						assert(it->pulse*length + (t.time-(it->edge))/binwidth >= 0);
						
						//here the counts are directly sorted into the appropriate windows
						if ( (t.time-(it->edge))/binwidth >= win_low && (t.time-(it->edge))/binwidth < win_high){
							data[y*pixel_count*2*sequence_length + x*2*sequence_length + it->pulse*2 + 0]++;
						}
						if ( (t.time-(it->edge))/binwidth >= refwin_low && (t.time-(it->edge))/binwidth < refwin_high){
							data[y*pixel_count*2*sequence_length + x*2*sequence_length + it->pulse*2 + 1]++;
						}
					}
				}
			}
		}
	}
private:
	int channel_0;
	int channel_1;
	int length, sequence_length, pixel_count, line_count;
	long long binwidth;
	int shot_trigger, sequence_trigger, pixel_trigger, line_trigger;

	int win_low, win_high, refwin_low, refwin_high;
	int x,y;

	int *data;
	int datalength;

	std::list<_PulsedAFMEdge> edge;

	bool waiting_for_sync;
	int pulse, counts;

	//Variable to take care of correct triggering between forward and backward scans
	int backward;

};
