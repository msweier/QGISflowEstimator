# -*- coding: utf-8 -*-
"""
/***************************************************************************
 FlowEstimator
                                 A QGIS plugin
 Estimates steady, uniform flow using the Manning equation for trapezoidal and DEM sampled channels.
                              -------------------
        begin                : 2015-05-21
        git sha              : $Format:%H$
        copyright            : (C) 2015 by M. Weier - North Dakota State Water Commision
        email                : mweier@nd.gov
 ***************************************************************************/

/***************************************************************************
 *                                                                         *
 *   This program is free software; you can redistribute it and/or modify  *
 *   it under the terms of the GNU General Public License as published by  *
 *   the Free Software Foundation; either version 2 of the License, or     *
 *   (at your option) any later version.                                   *
 *                                                                         *
 ***************************************************************************/
 """
import locale

from qgis.core import QgsMapLayerRegistry, QgsRaster, QgsMapLayer, QgsPoint

def frange(start, end, step):
  while start < end:
    yield start
    start += step

    
def getRasterLayerNames():
    layerMap = QgsMapLayerRegistry.instance().mapLayers()
    layerNames = []
    for name, layer in layerMap.iteritems():
        if layer.type() == QgsMapLayer.RasterLayer and layer.providerType() != 'wms':
            srs = layer.crs().authid()
            layerNames.append(unicode(layer.name()+' '+srs))
    return sorted(layerNames, cmp=locale.strcoll)
                
def getRasterLayerByName(layerName):
    layerMap = QgsMapLayerRegistry.instance().mapLayers()
    for name, layer in layerMap.iteritems():
        if layer.type() == QgsMapLayer.RasterLayer and layer.name() == layerName:
            if layer.isValid():
                return layer
            else:
                return None
                
def valRaster(x,y,rLayer):

    z = rLayer.dataProvider().identify(QgsPoint(x,y), QgsRaster.IdentifyFormatValue).results()[1]
    return z
    
def calcElev(self):
  
    features = self.vLayer.getFeatures()
    for f in features:
        geom = f.geometry()
    startPoint = geom.asPolyline()[0]
    endPoint = geom.asPolyline()[-1]
    try:
        startPointZdem = valRaster(startPoint[0],startPoint[1],self.rLayer)
    except:
        startPointZdem =None
        self.labelStartDepth.setText('Start point outside of raster')
        self.btnOk.setEnabled(False)
    try:        
        endPointZdem = valRaster(endPoint[0],endPoint[1],self.rLayer)
    except:
        endPointZdem =None
        self.labelStartDepth.setText('End point outside of raster')
        self.btnOk.setEnabled(False)
    return [startPointZdem, endPointZdem]

def elevationSampler(vectSHP,res,raster):
    "Returns xyz and station distance list from 2d vector and DEM at specified resolution"
    x = []
    y = []
    z = []
    dist = []
    vectLength=vectSHP.length
    for currentDist  in frange(0,vectLength,res):  
        #print currentDist
        # creation of the point on the line
        point = vectSHP.interpolate(currentDist)
        xp,yp=point.x, point.y
        x.append(xp)
        y.append(yp)
        #print x, y
        # extraction of the elevation value from the point
        zp=valRaster(xp,yp,raster)
        z.append(zp)
        dist.append(currentDist)
        xyzdList = [x,y,z,dist]
    return xyzdList

