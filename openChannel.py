# -*- coding: utf-8 -*-
"""
Created on Tue May  5 16:26:25 2015

@author: mweier
"""
#import matplotlib.pyplot as plt
import numpy as np
from shapely.geometry import LineString  




def channelBuilder(wsDepth, rightSS, leftSS, widthBottom):
    """
    Builds trapziodal channel station/elevation array given depth, 
    right side slope, left side slope, and bottom width
    """
    leftToe = wsDepth*1.25*leftSS
    rightToe = wsDepth*1.25*rightSS  
    staElev = np.array([(0.0, wsDepth*1.25), (leftToe, 0.0), (leftToe+widthBottom, 0.0), (leftToe+widthBottom+rightToe, wsDepth*1.25)])
    return staElev


def lineIntersection(line1, line2):
    xdiff = (line1[0][0] - line1[1][0], line2[0][0] - line2[1][0])
    ydiff = (line1[0][1] - line1[1][1], line2[0][1] - line2[1][1])
    def det(a, b):
        return a[0] * b[1] - a[1] * b[0]

    div = det(xdiff, ydiff)
    if div == 0:
        x = y = np.nan
        print 'lines do not intersect'
        return x, y

    d = (det(*line1), det(*line2))
    x = det(d, xdiff) / div
    y = det(d, ydiff) / div
    return x, y

def polygonArea(corners):
    area = 0.0
    for i in range(len(corners)):
        j = (i + 1) % len(corners)
        area += corners[i][0] * corners[j][1]
        area -= corners[j][0] * corners[i][1]
    area = abs(area) / 2.0
    return area  
    
def channelPerimeter(corners):
    P = 0.0
    for i in range(len(corners)-1):
        P += np.sqrt((np.power((corners[i+1][0]-corners[i][0]),2) + np.power((corners[i+1][1]-corners[i][1]),2)))
    return P
    

def flowEstimator(wsElev, n, channelSlope, **kwargs):
    """
    Estimates uniform flow using the Manning equation for
    a user defined trapziodal channel or a manually defined channel using
    a station/elevation file 
    """
    if kwargs.get("elevFile") is not None:
        staElev = np.genfromtxt(kwargs.get("elevFile"), delimiter = '\t')
    elif kwargs.get("staElev") is not None:
        staElev = kwargs.get("staElev")
    elif kwargs.get("widthBottom") and kwargs.get("rightSS") and kwargs.get("leftSS") > 0:
        staElev = channelBuilder(wsElev, kwargs.get("rightSS"), kwargs.get("leftSS"), kwargs.get("widthBottom"))
    else:
        print """
        Whoops, wrong input
        """
        return
    if kwargs.get("units") == "m":
        const = 1.0
    else:
        const = 1.49
    
#    intersectList = []
#    for i in range(0, len(staElev)):
#        x, y = lineIntersection((staElev[i-1], staElev[i]), ([staElev[0][0],wsElev], [staElev[-1][0],wsElev]))  
#        if x >= staElev[i-1][0] and x <= staElev[i][0] and abs(y - wsElev)<0.01:
#            #print x,y
#            intersectList.append((x,y))
#        else:
#            
#            #print 'line segments do not intersect'
#            pass
#    intersectArray = np.array(intersectList)
#    intersectArray = intersectArray[intersectArray[:,0].argsort()]
#    if len(intersectArray) > 2:
#        print 'more than two points intersect'
#        staMinElev = staElev[np.where(staElev[:,1]==min(staElev[:,1]))][0][0]
#        startPoint = intersectArray[np.where(intersectArray[:,0]<staMinElev)][-1]
#        endPoint = intersectArray[np.where(intersectArray[:,0]>staMinElev)][0]
        #intersectArray = np.vstack([startPoint, endPoint])
    thalweig = staElev[np.where(staElev[:,1] == np.min(staElev[:,1]))] 
    thalweigX = thalweig[:,0][0]
    minElev = thalweig[:,1][0]
    maxDepth = wsElev-minElev
    groundLine = LineString(staElev) 
    wsLine = LineString([[np.min(staElev[:,0]), wsElev], [np.max(staElev[:,0]), wsElev]])
    intersectArray = np.array(groundLine.intersection(wsLine))
    
    
    try:
        intersectArray = np.vstack([intersectArray[np.where(intersectArray[:,0]<thalweigX)][-1], intersectArray[np.where(intersectArray[:,0]>thalweigX)][0]])
        
    except:
        #print 'error'
        return 0, 0, 0, 0, 0, 0, staElev[:,0], staElev[:,1],staElev[:,0], staElev[:,0], np.ones(len(staElev[:,0]))*wsElev, staElev[:,0]
    

    
    staMin = np.min(intersectArray[:,0])
    staMax = np.max(intersectArray[:,0]) 
    

    staElevTrim = np.vstack([intersectArray[0], staElev, intersectArray[1]])
    #staElevTrim = staElevTrim[staElevTrim[:,0].argsort()]
    staElevTrim = staElevTrim[np.where((staElevTrim[:,0]>=staMin) & (staElevTrim[:,0]<=staMax))]
    
    area = polygonArea(staElevTrim)
    R = area/channelPerimeter(staElevTrim)
    v = (const/n)*np.power(R,(2./3.0))*np.sqrt(channelSlope)
    Q = v*area
    topWidth = staMax-staMin 
    xGround = staElev[:,0]
    yGround = staElev[:,1]
    yGround0 = np.ones(len(xGround))*np.min(yGround)     
    xWater = staElevTrim[:,0]
    yWater = np.ones(len(xWater))*wsElev
    yWater0 = staElevTrim[:,1]  
    args = R, area, topWidth, Q, v, maxDepth, xGround, yGround, yGround0, xWater, yWater, yWater0
    return args

#def plotter(args):
#    R, area, topWidth, Q, v, xGround, yGround, yGround0, xWater, yWater, yWater0 = args
#    plt.plot(xGround, yGround, '0.9')
#    plt.fill_between(xGround, yGround, yGround0, where=yGround>yGround0, facecolor='0.9', interpolate=True)
#    plt.plot(xWater, yWater, 'blue')
#    plt.fill_between(xWater, yWater, yWater0, where=yWater>=yWater0, facecolor='blue', interpolate=True, alpha = 0.1)
#    plt.xlabel('Station')
#    plt.ylabel('Elevation')
#    plt.show() 
#    print 
#    print 'Hydraulic Radius = ',R
#    print 'Area = ',area, 'sq ft'
#    print 'Top Width = ',topWidth, 'ft'
#    print 'Flow = ',Q, 'cfs'
#    print 'Velocity = ',v, 'ft/s'      
 
#wsElev = 10.
#n = 0.040
#channelSlope = 0.0005
#
#elevFile = '/Users/mweier/Desktop/XScsv.txt'
#
#widthBottom = 40.
#rightSS = 5. #eg 2:1
#leftSS = 5. #eg 2:1
#
#R, area, topWidth, Q, v, xGround, yGround, yGround0, xWater, yWater, yWater0= flowEstimator(wsElev, n, channelSlope, widthBottom = 40., rightSS = 5., leftSS = 5.)
#plotter(R, area, topWidth, Q, v, xGround, yGround, yGround0, xWater, yWater, yWater0)
#    
#    
#R, area, topWidth, Q, v, xGround, yGround, yGround0, xWater, yWater, yWater0 = flowEstimator(1900.25, n, channelSlope, elevFile = elevFile)
#plotter(R, area, topWidth, Q, v, xGround, yGround, yGround0, xWater, yWater, yWater0)