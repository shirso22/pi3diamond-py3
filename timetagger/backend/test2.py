import time

import TimeTagger

# o = TimeTagger.OverFlow()
# set print thread-events 0
"""
d = [TimeTagger.Distribution(i) for i in range(16)]
h = [TimeTagger.Histogram(i) for i in range(16)]

time.sleep(1)


for i in range(16):
    d[i].clear()
    h[i].clear()
    
    
time.sleep(5)

for i in range(16):
    data = d[i].getData()
    if sum(data):
        data = filter(lambda x: x>0, data)
        data = map(lambda x:6000*float(x)/sum(data), data)

        y = sum(data) / len(data)
        o = math.sqrt(sum(map(lambda x: (x-y)**2, data)) / len(data))
        data = numpy.array(map(int, data))

        print "Channel: %d" % (i,)
        print d[i].getData()
        print data
        print "Mittelwert: %s ps" % (y,)
        print "Standartabweichung: %s ps" % (o, )
        print "Maximale Fenstergroesse: %s ps" % (max(data),)

        print h[i].getData()
"""

sleeptime = 1
directory = 'Test-4'
# print 'which channel?'
# channel = int(sys.stdin.readline())

c0 = TimeTagger.Countrate(0)
c1 = TimeTagger.Countrate(1)
c2 = TimeTagger.Countrate(2)
c3 = TimeTagger.Countrate(3)
c4 = TimeTagger.Countrate(4)
c5 = TimeTagger.Countrate(5)
c6 = TimeTagger.Countrate(6)

amLeben = True

# c = TimeTagger.Counter(channel,1000**4)
# o = TimeTagger.OverFlow()

while amLeben:
    print "ch0: %d" % (c0.getData(),)
    print "ch1: %d" % (c1.getData(),)
    print "ch2: %d" % (c2.getData(),)
    print "ch3: %d" % (c3.getData(),)
    print "ch4: %d" % (c4.getData(),)
    print "ch5: %d" % (c5.getData(),)
    print "ch6: %d" % (c6.getData(),)
    print
    c0.clear()
    c1.clear()
    c2.clear()
    c3.clear()
    c4.clear()
    c5.clear()
    c6.clear()
    time.sleep(0.5)
