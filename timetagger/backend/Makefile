all: TimeTagger _TimeTagger.so

CFLAGS=-g -O2 -Wall -fPIC -DLINUX
TOOLS=Histogram.o Iterator.o Pulsed.o CountBetweenMarkers.o Counter.o

clean:
	rm -f *.o TimeTagger _TimeTagger.so *~ *pyc TimeTagger_wrap.cxx gmon.out TimeTagger.py

TimeTagger: TimeTagger.o okFrontPanelDLL.o TimeTaggerTest.o $(TOOLS)
	g++ $(CFLAGS) $^ -o TimeTagger -ldl -lboost_thread-mt

%.o: %.cpp TimeTagger.h
	g++ -c $(CFLAGS) $<

TimeTagger_wrap.cxx: TimeTagger.i TimeTagger.h $(TOOLS)
	swig -Wall -c++ -python TimeTagger.i

TimeTagger_wrap.o: TimeTagger_wrap.cxx
	g++ -c $(CFLAGS) -I/usr/include/python2.7 $<

_TimeTagger.so: TimeTagger_wrap.o okFrontPanelDLL.o TimeTagger.o $(TOOLS)
	g++ -shared $^ -o _TimeTagger.so -lboost_thread-mt
