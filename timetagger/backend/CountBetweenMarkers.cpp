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
// PY3-PORT: superseded by <chrono>.

#include "TimeTagger.h"

using namespace std;

class CountBetweenMarkers : public _Iterator {
public:
	CountBetweenMarkers(int _counter, int _marker, int _bins) {
		counter = _counter;
		marker = _marker;
		bins = _bins;
		
		data = new int[bins];
		
		clear();
		
		registerChannel(counter);
		registerChannel(marker);
		
		start();
	}

	virtual ~CountBetweenMarkers() {
		stop();
		delete [] data;
	}

	virtual void clear() {
		lock();
		
		state = -1;
		for(int i=0; i<bins; i++)
			data[i] = 0;
		
		unlock();
	}
	
	bool ready() {
		lock();
		bool wert = state >= bins;
		unlock();
		
		return wert;
	}

	void getData(int **ARGOUTVIEWM_ARRAY1, int *DIM1, bool blocking=0) {
		assert(data);
		
		int *arr = new int[bins];
		
		assert(arr);

		while(blocking && !ready())
			std::this_thread::sleep_for(std::chrono::milliseconds(10));

		lock();

		for ( int i=0; i<bins; i++) {
			arr[i] = data[i];
		}

		*ARGOUTVIEWM_ARRAY1 = arr;
		*DIM1 = bins;
		
		unlock();
	}

protected:
	virtual void next(Tag* list, int count, long long time) {
		for(int i=0; i<count; i++) {
			if(list[i].chan == marker && state < bins)
				state++;
			if(list[i].chan == counter && state >= 0 && state < bins) {
				data[state]++;
			}
		}
	}

private:
	int *data;
	
	int counter;
	int marker;
	int bins;
	
	int state;
};