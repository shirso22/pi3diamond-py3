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

#include "Iterator.cpp"


using namespace std;

int main() {
	OverFlow o;
	Iterator it(7);
	while(long long time = it.next()) {
		std::cout << time << std::endl;
	}

}