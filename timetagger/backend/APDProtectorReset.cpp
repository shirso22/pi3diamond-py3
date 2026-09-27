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

class APDProtectorReset : public _Tagger {
public:
	void setWire(int addr, UINT32 value) {
		int err = 0;
		if(!err && (err = xem->SetWireInValue(addr, value))) {
			std::cout << "Uploading empty threshold faild" << std::endl;
		}
	
		if(!err) {
			xem->UpdateWireIns();
			//xem->SetTimeout(1000); // set timeout to 1s
		}
	}
};