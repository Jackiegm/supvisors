#!/usr/bin/python
#-*- coding: utf-8 -*-

# ======================================================================
# Copyright 2016 Julien LE CLEACH
# 
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
# 
#     http://www.apache.org/licenses/LICENSE-2.0
# 
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
# ======================================================================

from math import sqrt
from time import gmtime, localtime, strftime, time


# strings used as headers in messages between Listener and MainLoop
TICK_HEADER = u'tick'
PROCESS_HEADER = u'process'
STATISTICS_HEADER = u'statistics'

# strings used as headers in messages between EventPublisher and Supervisors' Client
SupervisorsStatusHeader = u'supervisors'
RemoteStatusHeader = u'remote'
ApplicationStatusHeader = u'application'
ProcessStatusHeader = u'process'


# used to convert enumeration-like value to string and vice-versa
def enumToString(dico,  idxEnum):
    return next((name for name, value in dico.items() if value == idxEnum),  None)

def stringToEnum(dico,  strEnum):
    return next((value for name, value in dico.items() if name == strEnum),  None)

def enumValues(dico):
    return [ y for (x, y) in dico.items() if not x.startswith('__') ]

def enumStrings(dico):
    return [ x for x in dico.keys() if not x.startswith('__') ]


def supervisors_short_cuts(instance, lst):
    """ Used to set shortcuts in object attributes against supervisors attributes. """
    for attr in lst:
        setattr(instance, attr, getattr(instance.supervisors, attr))


# return time without date
def simpleLocalTime(now=None):
    if now is None: now = time()
    return strftime("%H:%M:%S", localtime(now))

def simpleGmTime(now=None):
    if now is None: now = time()
    return strftime("%H:%M:%S", gmtime(now))


# simple lambda functions
mean = lambda x: sum(x) / float(len(x))
srate = lambda x, y: 100.0 * x / y - 100.0 if y else float('inf')
stddev = lambda lst, avg: sqrt(sum((x - avg) ** 2 for x in lst) / len(lst))

# linear regression
def getLinearRegression(xData, yData):
    try:
        import numpy
        return numpy.polyfit(xData, yData, 1)
    except ImportError:
        # numpy not available
        # try something approximate and simple
        dataSize = len(xData)
        sumX = sum(xData)
        sumY = sum(yData)
        sumXX= sum(map(lambda x: x * x, xData))
        sumProducts = sum([ xData[i] * yData[i] for i in range(dataSize) ])
        a = (sumProducts - sumX * sumY / dataSize) / (sumXX - (sumX * sumX) / dataSize)
        b = (sumY - a * sumX) / dataSize
        return a, b

def getSimpleLinearRegression(lst):
    # in Supervisors, Y data is periodic
    dataSize = len(lst)
    return getLinearRegression( [ i for i in range(dataSize) ], lst)

# get statistics from data
def getStats(lst):
    rate = a = b = dev = None
    # calculate mean value
    avg = mean(lst)
    if len(lst) > 1:
        # calculate instant rate value between last 2 values
        rate = srate(lst[-1], lst[-2])
        # calculate slope value from linear regression of values
        a, b = getSimpleLinearRegression(lst)
        # calculate standard deviation
        dev = stddev(lst, avg)
    return avg, rate, (a,  b), dev
