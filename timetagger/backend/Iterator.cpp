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
#include <queue>
#include <fstream>
#include <iostream>

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

class Iterator : public _Iterator {
public:
	Iterator(int chan) {
		registerChannel(chan);
		channel = chan;
		clear();
		start();
	}

	virtual ~Iterator() {
		stop();
	}

	Iterator* __iter__() {
		return this;
	}

	long long next() {
		while(1) {
			lock();
			bool empty = q.empty();
			long long wert = 0;
			if(!empty) {
				wert = q.front();
				q.pop();
			}
			unlock();

			if(!empty)
				return wert;

			std::this_thread::sleep_for(std::chrono::milliseconds(10));
		}
	}
	
	int size() {
		lock();
		int wert = q.size();
		unlock();
		return wert;
	}
	
	virtual void clear() {
		lock();
		q = std::queue<long long>();
		unlock();
	}

protected:
	virtual void next(Tag* list, int count, long long time) {
		for(int i=0; i<count; i++) {
			if(list[i].overflow) {
				// TODO: push StopIteration
			} else if(list[i].chan == channel)
				q.push(list[i].time);
		}
	}

private:
	std::queue<long long> q;
	int channel;
};


class OverFlow : public _Iterator {
public:
	OverFlow() { 
		clear();
		start(); 
	}
	
	virtual ~OverFlow() {
		stop();
	}
	
	virtual void clear() {
		lock();
		overflows = 0;
		show_next = 1;
		std::cout << "clear overflows..." << std::endl;
		unlock();
	}
	
	long long overflows;
	
protected:
	virtual void next(Tag* list, int count, long long time) {
		for(int i=0; i<count; i++)
			if(list[i].overflow) {
				overflows++;
				if(show_next || (overflows % 100) == 0) { 
					std::cout << "Overflows: " << overflows << std::endl;
					show_next = 0;
				}
			}
			if(time > 1e12)
				show_next = 1;
	}
	
private:
	bool show_next;
};


class Dump : public _Iterator {
public:
	Dump(std::string _filename) {
		filename = _filename;
		output_file = 0;
		clear();
		start();
	}
	
	~Dump() {
		stop();
		output_file->close();
		delete output_file;
	}
	
	virtual void clear() {
		lock();
		if(output_file) {
			output_file->close();
			delete output_file;
		}
		output_file = new std::ofstream(filename.c_str(), std::ios::out | std::ios::trunc | std::ios::binary);
		unlock();
	}
protected:
	virtual void next(Tag* list, int count, long long time) {
		output_file->write( (char*)list, count * sizeof(Tag));
	}
private:
	std::ofstream *output_file;
	std::string filename;
};


class Chans : public _Iterator {
public:
	Chans() {
		start();
	}
	virtual ~Chans() {
		stop();
	}
	void registerChannel(int chan) {
		_Iterator::registerChannel(chan);
	}
	void unregisterChannel(int chan) {
		_Iterator::unregisterChannel(chan);
	}
	virtual void clear() {
		for(int i=0; i<channels; i++)
			_Iterator::unregisterChannel(i);
	}
protected:
	virtual void next(Tag* list, int count, long long time) {}
};

