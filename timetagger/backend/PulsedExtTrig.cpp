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

struct _PulsedEdgeExtTrig {
	long long edge;
	int pulse;
};

class PulsedExtTrig : public _Iterator {
public:
	PulsedExtTrig(int _length, long long _binwidth, int _sequence_length, int _channel,
		          int _channel2, int _shot_trigger=-1, int _sequence_trigger=-1, int _bin_trigger=-1,
		          int _trig1=-1, int _trig2=-1, bool _dual_sequence=true) {
		channel = _channel;
		channel2 = _channel2;

		shot_trigger = _shot_trigger;
		sequence_trigger = _sequence_trigger;
		sequence_length = _sequence_length;
		bin_trigger = _bin_trigger;
		trig1 = _trig1;
		trig2 = _trig2;

		length = _length;
		binwidth = _binwidth;
		dual_sequence = _dual_sequence;

		dual_toggle = 0;

		if(channel>=0)
			registerChannel(channel);
		if(channel2>=0)
			registerChannel(channel2);
		if(shot_trigger>=0)
			registerChannel(shot_trigger);
		if(sequence_trigger>=0)
			registerChannel(sequence_trigger);
		if(bin_trigger>=0)
			registerChannel(bin_trigger);
		if(trig1>=0)
			registerChannel(trig1);
		if(trig2>=0)
			registerChannel(trig2);

		data = new int[length*sequence_length];
		if(!data)
			cout << "Warning: Konnte Speicher nicht allocieren" << endl;

		clear();

		start();
	}

	virtual ~PulsedExtTrig() {
		stop();
		if(data)
			delete [] data;
	}
	
	virtual void start() {
		lock();
		waiting_for_sync = (sequence_trigger>=0) ? 1 : 0;
		pulse = -1;
		counts = 0;
		dual_toggle = 0;
		unlock();
		_Iterator::start();
	}

	void getData(int **ARGOUTVIEWM_ARRAY2, int *DIM1, int *DIM2) {
		if(!data) {ARGOUTVIEWM_ARRAY2 = 0; DIM1 = 0; DIM2 = 0; return;}

		int *arr = new int[length*sequence_length];
		if(!arr) {ARGOUTVIEWM_ARRAY2 = 0; DIM1 = 0; DIM2 = 0; return;}

		lock();

		for ( int i=0; i<length*sequence_length; i++) {
			arr[i] = data[i];
		}

		*ARGOUTVIEWM_ARRAY2 = arr;
		*DIM1 = sequence_length;
		*DIM2 = length;

		unlock();
	}

	// Returns 'sequence_number' variable, which is the number of done sweeps.
	int getSequenceNumber() {
		return sequence_number;
	}

	// Returns 'counts' variable, which is the number total photon counts?!?.
	int getCounts() {
		return counts;
	}
	
	// Returns 'pulse' variable, which is the number bin_trigger receptions and thus a count of how
	// many frequency bins we alreday jumped in total.
	int getPulse() {
		return pulse;
	}

	// Method for manually resetting the sweep at the software level.
	// This should be used to circumvent the usage of a sequence_trigger.
	virtual void resetSweep() {
		pulse = -1;
		waiting_for_sync = 0;
		sequence_number++;
	}

	virtual void clear() {
		lock();

		for(int i=0; i<length*sequence_length; i++) {
			data[i] = 0;
		}

		waiting_for_sync = (sequence_trigger>=0) ? 1 : 0;
		pulse = -1;
		sequence_number = 0;
		counts = 0;
		dual_toggle = 0;

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

			// on sync
			if(t.chan == sequence_trigger) {
				if (waiting_for_sync)
				{
					pulse = -1;
					waiting_for_sync = 0;
					//dual_toggle = 0;
					sequence_number++;
				}
			}

			//on bin_trigger reception
			if (t.chan == bin_trigger && !waiting_for_sync)
			{
				if (dual_sequence)
					if (pulse==-1)
						pulse = 0;
					else
						pulse += 2;
				else
					pulse++;

				if(pulse > sequence_length) {
					waiting_for_sync = 1;
				}
			}

			//on trig1 reception
			if (t.chan == trig1)
			{
				dual_toggle = 0;
			}

			//on trig2 reception
			if (t.chan == trig2)
			{
				dual_toggle = 1;
			}

			//on laser trigger reception
			if(t.chan == shot_trigger && !waiting_for_sync) {
				//pulse++;
				
				//if(pulse >= sequence_length) {
				//	if(sequence_trigger>=0) {
				//		waiting_for_sync = 1;
				//	} else {
				//		//pulse = 0;
				//		sequence_number++;
				//	}
				//}
				if(pulse < sequence_length && pulse >= 0) {
					_PulsedEdgeExtTrig e;
					e.edge = t.time;
					e.pulse = pulse + dual_toggle;
					assert(pulse >= 0 && pulse < sequence_length);
					edge.push_back(e);
					//dual_toggle != dual_toggle;
					
				}

				/*if (dual_toggle == 0)
				{
					dual_toggle = 1;
				}
				else
				{
					dual_toggle = 0;
				}*/

				if(!edge.empty() && t.time - edge.front().edge > length*binwidth)
					edge.pop_front();
			}	

			// on photon in histogram range
			if ((t.chan == channel || t.chan == channel2) && !waiting_for_sync) {
				std::list<_PulsedEdgeExtTrig>::iterator it;
				for(it = edge.begin(); it != edge.end(); it++) {
					if( (t.time - (it->edge))/binwidth < length && (t.time - (it->edge))/binwidth >= 0) {
						counts++;
						/*if (dual_sequence)
							assert(it->pulse + 1 < sequence_length);
						else*/
						assert(it->pulse < sequence_length);
						assert(it->pulse >= 0);

						assert(it->pulse*length + (t.time-(it->edge))/binwidth < sequence_length*length);
						assert(it->pulse*length + (t.time-(it->edge))/binwidth >= 0);

						/*if (dual_sequence)
						{
							data[(it->pulse + dual_toggle)*length + (t.time-(it->edge))/binwidth]++;
						}
						else
						{*/
						data[it->pulse*length + (t.time-(it->edge))/binwidth]++;
						//}
					}
				}
			}
		}
	}
private:
	int channel;
	int channel2;
	int length, sequence_length;
	long long binwidth;
	int shot_trigger, sequence_trigger, bin_trigger, trig1, trig2;
	bool dual_sequence;
	int dual_toggle;
	int *data;

	std::list<_PulsedEdgeExtTrig> edge;

	bool waiting_for_sync;
	int pulse, sequence_number, counts;

};
