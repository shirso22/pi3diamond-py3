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
#ifndef TIMETAGGER_H
#define TIMETAGGER_H

// PY3-PORT: boost_thread 1.47 replaced with the C++11 standard library.
// boost/thread.hpp also pulled in <cassert> and <map> transitively;
// the standard headers do not, so they are declared explicitly.
#include <cassert>
#include <map>
#include <vector>
#include <string>
#include <cstring>
#include <atomic>
#include <mutex>
#include <thread>
#include <chrono>
#include <string>
#include "okFrontPanelDLL.h"

const std::string bitfilename = "TimeTaggerController.bit";		// location of bitfile for fpga
const int bytes_per_word = 4;									

const int workers = 4; 											// count of threads
const int channels = 8*2;										// musst be the same as on the FPGA
																// *2 ist for up/down
const int distribution = 1<<7;									// 7 Bit für Zeitauflösung
const int picosecounds = 6000;									// time delay for each macro cycle

const int blocksize = 1024;										// size of data, transmitted at once [byte]
const int ibuffersize = blocksize * 256;						// data to read and convert at once [byte]
const int obuffersize = ibuffersize / bytes_per_word;			// buffer size for output, do not change [tag]


class _Iterator;
class _Tagger;
class _Worker;
class _Iter;

struct Tag {
	bool overflow;
	int chan;
	long long time;
};

class _Tagger {
public:
	static _Tagger* getTagger(_Iterator *it);

	_Iter* addIterator(_Iterator *it);
	
	void registerChannel(int chan);
	void unregisterChannel(int chan);
	
	static void getDistributionCount(int c, double **ARGOUTVIEWM_ARRAY1, int *DIM1);
	static void setSerial(std::string s);
	static void SetWireIn(int addr, int value);
	
	void iter(_Worker *w);
	/*void SetWireIn(int addr, int value);*/

	okCFrontPanel *xem;

	

private:
	
	_Worker* worker[workers];
	
	_Tagger();
	~_Tagger();

	void configureFpga();
	void configureChannel();

	void start();
	void stop();

	void read(_Worker *w);
	void convert(_Worker *w);

	void warning(int lvl, const char* msg);
	void update_distribution();
	int setFilter(bool state);

	// Tagger Loader
	static _Tagger* tagger;
	static std::string serial;
	static std::mutex tagger_mutex;
	std::mutex warning_mutex;

	// FPGA Connection
	okCPLL22150 *pll;
	int chans[channels];
	bool fpga_connected;
	bool suppress_warnings;
	bool fpga_channel_reconfig;
	std::mutex channel_mutex;

	// Buffer Mutexes
	std::mutex read_mutex;
	std::mutex convert_mutex;
	
	// Convert Data
	long long rollover;
	long long distribution_counts[channels][distribution];
	long long distribution_ps[channels][distribution];

	// iterator
	_Iter* iterators;
};

/** Base class for all ITerators
 */
class _Iterator {
public:
	/** standart constructor
	 * will register with the default TimeTagger
	 * note: running _must_ be set to one in child class
	 */
	_Iterator();
	virtual ~_Iterator();
	
	void _next(_Worker* w);
	
	virtual void start();
	virtual void stop();

protected:
	void registerChannel(int chan);
	void unregisterChannel(int chan);
	
	void lock();
	void unlock();
	
	virtual void next(Tag* list, int count, long long time) = 0;
	virtual void clear() = 0;
	
	_Tagger* tagger;

private:
	
	bool chans[channels];
	_Iter* iter;
	bool running;
	
};

class _Worker {
public:
	_Worker(_Tagger* t);
	~_Worker();
	
	void terminate() { run = false; }

	// Buffer between FPGA-Fifo and PC
	unsigned char ibuffer[ibuffersize];
	int ifull_usage;

	// Buffer after convertion
	Tag obuffer[obuffersize];
	int obuffer_usage;
	long long time;

private:
	void work();
	
	// worker thread
	std::atomic<bool> run;			// PY3-PORT: was a plain bool -- data race with work()
	std::thread thread;
	_Tagger* tagger;
	
};

class _Iter {
public:
	_Iter() { next=0; iter=0; };
	
	_Iter* next;
	_Iterator* iter;
	
	std::mutex* getMutex() { return &mutex; };
	
private:
	std::mutex mutex;
};


#endif
