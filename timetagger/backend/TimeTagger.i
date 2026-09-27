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
#ifndef WRAPPER_SWIG_I
#define WRAPPER_SWIG_I
%module TimeTagger
// first section
%{
#include "TimeTagger.h"
#include "Iterator.cpp"
#include "Histogram.cpp"
#include "Pulsed.cpp"
#include "PulsedAFM.cpp"
#include "PulsedExtTrig.cpp"
#include "CountBetweenMarkers.cpp"
#include "Counter.cpp"

//#include "okFrontPanelDLL.cpp"

#include "numpy/arrayobject.h"
%}
// second section

// PY3-PORT: translate C++ exceptions into Python ones.
//
// Without this, a throw on a WRAPPED call -- runtime_error("Could not load
// FrontPanel DLL.") is the one you will actually meet -- escapes into the
// interpreter's C frame, std::terminate runs, and the PROCESS DIES.
//
// This does NOT cover the worker threads. _Worker::work() never crosses a SWIG
// wrapper, so %exception cannot see it; that case is handled by a try/catch
// inside work() itself, added by modernize_timetagger.py. No traceback, no log entry, not even `python -i` keeps the
// prompt: you land back at the shell. That was the behaviour under SWIG 3.0.7
// and Python 2 as well.
//
// With it, the same failure arrives as a Python RuntimeError carrying
// e.what(), which is the difference between "the interpreter vanished" and a
// message naming the problem while you are standing at the instrument.
%include "exception.i"
%exception {
    try {
        $action
    } catch (const std::exception &e) {
        SWIG_exception(SWIG_RuntimeError, e.what());
    } catch (...) {
        SWIG_exception(SWIG_RuntimeError, "unknown C++ exception in TimeTagger");
    }
}

%include "numpy.i"
%include "std_string.i"
%init %{
	import_array();
%}

%include "TimeTagger.h"
%include "Iterator.cpp"
%include "Histogram.cpp"
%include "Counter.cpp"
%include "Pulsed.cpp"
%include "PulsedAFM.cpp"
%include "PulsedExtTrig.cpp"
%include "CountBetweenMarkers.cpp"

//%include "okFrontPanelDLL.cpp"

#endif
