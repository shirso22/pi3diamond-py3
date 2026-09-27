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

#include <queue>
#include <fstream>
#include <iostream>

#include "TimeTagger.h"

class Histogram : public _Iterator {
public:
	Histogram(int chan, int chan2 = -1, long long binwidth=1000) {
		channel  = chan; 
		channel2 = chan2==-1?chan:chan2;
		this->binwidth = binwidth;
		registerChannel(chan);
		registerChannel(chan2); 
		clear(); 
		start();
	}
	
	virtual ~Histogram() {
		stop();
	}
	
	virtual void start() {
		lock();
		last = 0;
		unlock();
		_Iterator::start();
	}

	void getData(long long **ARGOUTVIEWM_ARRAY2, int *DIM1, int *DIM2) {
		lock();
		int s = data.size();
		long long *arr = new long long[s*2];
		std::map<long long,long long>::iterator it;
		int i=0;

		for ( it=data.begin() ; it != data.end(); it++ ) {
			arr[i++] = it->first*binwidth;
			arr[i++] = it->second;
		}

		*ARGOUTVIEWM_ARRAY2 = arr;
		*DIM1 = s;
		*DIM2 = 2;
		unlock();
	}

	virtual void clear() {
		lock();
		last = 0;
		data = std::map<long long,long long>();
		unlock();
	}
protected:
	virtual void next(Tag* list, int count, long long time) {
		for(int i = 0; i < count; i++) {
			if(list[i].overflow) {
				last = 0;
			} else if(list[i].chan == channel && last != 0) {
				data[(list[i].time - last)/binwidth] += 1;
				if(channel == channel2)
					last = list[i].time;
				else
					last = 0;
			} else if(list[i].chan == channel2)
				last = list[i].time;
		}
	}
private:
	std::map<long long,long long> data;
	int channel;
	int channel2;
	long long binwidth;
	long long last;
};

const int bins_per_clock = 64;

class Distribution : public _Iterator {
public:
	Distribution(int chan) {
		channel = chan;
		registerChannel(chan);
		clear();
		start();
	}
	
    virtual ~Distribution() {
		stop();
	}

	void getData(long long **ARGOUTVIEWM_ARRAY1, int *DIM1) {
		lock();
		long long *arr = new long long[bins_per_clock];

		for ( int i=0; i<bins_per_clock; i++ )
			arr[i] = counts[i];

		*ARGOUTVIEWM_ARRAY1 = arr;
		*DIM1 = bins_per_clock;
		unlock();
	}

	virtual void clear() {
		lock();
		for(int i=0; i<bins_per_clock; i++)
			counts[i]=0;
		unlock();
	}

protected:
	virtual void next (Tag *list, int count, long long time) {
		for(int i = 0; i < count; i++) {
			if(list[i].chan == channel) {
				counts[list[i].time%bins_per_clock]++;
			}
		}
	}
private:
	int channel;
	long long counts[bins_per_clock];
};
