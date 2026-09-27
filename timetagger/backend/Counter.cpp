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

#include "TimeTagger.h"

using namespace std;

class Counter : public _Iterator {
public:
	Counter(int _chan, long long _binwidth, int _bins = 1) {
		chan = _chan;
		binwidth = _binwidth;
		bins = _bins;
		
		data = new int[bins + 1];
		
		clear();
		
		registerChannel(chan);
		
		start();
	}

	virtual ~Counter() {
		stop();
		delete [] data;
	}

	virtual void clear() {
		lock();
		
		pos = 0;
		starttime = -1;
		
		for(int i=0; i<bins+1; i++)
			data[i] = 0;
		
		unlock();
	}

	void getData(int **ARGOUTVIEWM_ARRAY1, int *DIM1) {
		assert(data);
		int *arr = new int[bins];
		assert(arr);

		lock();

		for ( int i=0; i<bins; i++) {
			arr[i] = data[(i + pos + 1) % (bins+1)];
		}

		*ARGOUTVIEWM_ARRAY1 = arr;
		*DIM1 = bins;
		
		unlock();
	}

protected:
	virtual void next(Tag* list, int count, long long time) {
		for(int i=0; i<count; i++) {
			if(list[i].overflow) {
				starttime = -1;
				pos = 0;
			} else if(list[i].chan == chan) {
				// erster durchlauf nach clean
				if(starttime == -1) starttime = list[i].time;
				
				// lange kein paket mehr gesehen
				if(list[i].time >= starttime + binwidth*(bins+1)) {
					pos = 0;
					starttime = list[i].time;
					
					for(int i=0; i<bins+1; i++)
						data[i] = 0;
				}
				
				// nicht mehr im aktuellen bin
				while(list[i].time >= starttime + binwidth) {
					starttime += binwidth;
					pos = (pos+1)%(bins+1);
					data[pos] = 0;
				}
				
				data[pos]++;
			}
		}
		// lange kein paket mehr gesehen
		if(time >= starttime + binwidth*(bins+1)) {
			pos = 0;
			starttime = time;
			
			for(int i=0; i<bins+1; i++)
				data[i] = 0;
		}
	}

private:
	int *data;
	
	int chan;
	long long binwidth;
	int bins;
	
	int pos;
	long long starttime;
};

class Countrate : public _Iterator {
public:
	Countrate(int _chan) {
		chan = _chan;
		
		clear();
		
		registerChannel(chan);
		start();
	}
	
	virtual ~Countrate() {
		stop();
	}
	
	double getData() {
		lock();
		double d;
		if(now == startzeit)
			d = 0;
		else
			d = 1.0e12*double(flanken)/double(now-startzeit);
		unlock();
		return d;
	}

	long long getTotalCounts(){
		return flanken;
	}

	void SetWireIn(int addr, int value){
		int err=0;
		
		/*if(!err && (err = tagger->xem->SetWireInValue(addr, value))) {
			std::cout << "Uploading empty threshold failed" << std::endl;
		}*/
	
		if(!err) {
			tagger->xem->UpdateWireIns();
		}
	}

	virtual void clear() {
		lock();
		flanken = -1;
		startzeit = 0;
		now = 0;
		unlock();
	}
	
protected:
	virtual void next(Tag* list, int count, long long time) {
		for(int i=0; i<count; i++) {
			if(list[i].overflow) {
				startzeit = 0;
				flanken = 0;
			} else if(list[i].chan == chan) {
				if(!startzeit) 
					startzeit = list[i].time;
				flanken++;
			}
		}
		now = time;
		if(!startzeit) startzeit = time;
	}
private:
	int chan;
	
	long long now;
	long long startzeit;
	long long flanken;
};

// helper class to reset the fuse...
class FuseReset : public _Iterator {
public:
	FuseReset(int _chan) {
		chan = _chan;
		
		//clear();
		
		//registerChannel(chan);
		//start();
	}
	
	virtual ~FuseReset() {
		//stop();
	}
	
	/*double getData() {
		lock();
		double d;
		if(now == startzeit)
			d = 0;
		else
			d = 1.0e12*double(flanken)/double(now-startzeit);
		unlock();
		return d;
	}

	long long getTotalCounts(){
		return flanken;
	}*/

	void SetWireIn(int addr, int value){
		int err=0;
		
		/*if(!err && (err = tagger->xem->SetWireInValue(addr, value))) {
			std::cout << "Uploading empty threshold failed" << std::endl;
		}*/
	
		if(!err) {
			tagger->xem->UpdateWireIns();
		}
	}

	virtual void clear() {
		lock();
		flanken = -1;
		startzeit = 0;
		now = 0;
		unlock();
	}
	
protected:
	virtual void next(Tag* list, int count, long long time) {
		for(int i=0; i<count; i++) {
			if(list[i].overflow) {
				startzeit = 0;
				flanken = 0;
			} else if(list[i].chan == chan) {
				if(!startzeit) 
					startzeit = list[i].time;
				flanken++;
			}
		}
		now = time;
		if(!startzeit) startzeit = time;
	}
private:
	int chan;
	
	long long now;
	long long startzeit;
	long long flanken;
};