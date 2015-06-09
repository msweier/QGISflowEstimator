# -*- coding: utf-8 -*-
"""
/***************************************************************************
 FlowEstimatorDialog
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

import os

from PyQt4 import QtGui, uic
from PyQt4.QtGui import QColor, QDialog, QMessageBox, QFileDialog
from PyQt4.QtCore import Qt, SIGNAL, QObject
from qgis.gui import QgsRubberBand
from qgis.core import QGis, QgsPoint

from matplotlib.backends.backend_qt4agg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.figure import Figure
from matplotlib.ticker import ScalarFormatter

import FlowEstimator_utils as utils
from openChannel import flowEstimator
from ptmaptool import ProfiletoolMapTool

from shapely.geometry import LineString
import numpy as np


FORM_CLASS, _ = uic.loadUiType(os.path.join(
    os.path.dirname(__file__), 'flow_estimator_dialog_base.ui'))


class FlowEstimatorDialog(QtGui.QDialog, FORM_CLASS):
    def __init__(self, iface, parent=None):
        """Constructor."""
        super(FlowEstimatorDialog, self).__init__(parent)
        # Set up the user interface from Designer.
        # After setupUI you can access any designer object by doing
        # self.<objectname>, and you can use autoconnect slots - see
        # http://qt-project.org/doc/qt-4.8/designer-using-a-ui-file.html
        # #widgets-and-dialogs-with-auto-connect
        #QDialog.__init__(self, None, Qt.WindowStaysOnTopHint)
        self.iface = iface
        self.setupUi(self)
        
        self.btnOk = self.buttonBox.button(QtGui.QDialogButtonBox.Ok)
        self.btnOk.setText("Save Data")
        self.btnClose = self.buttonBox.button(QtGui.QDialogButtonBox.Close) 
        self.btnBrowse.clicked.connect(self.writeDirName)
        self.btnLoadTXT.clicked.connect(self.loadTxt)
        self.btnSampleLine.setEnabled(False)
        self.btnSampleSlope.setEnabled(False)
        self.calcType = 'Trap'
      
        # add matplotlib figure to dialog
        self.figure = Figure()
        self.axes = self.figure.add_subplot(111)
        self.figure.subplots_adjust(left=.1, bottom=0.15, right=.78, top=.9, wspace=None, hspace=.2)
        self.mplCanvas = FigureCanvas(self.figure)
        
        
        #self.widgetPlotToolbar = NavigationToolbar(self.mplCanvas, self.widgetPlot)
        #lstActions = self.widgetPlotToolbar.actions()
        #self.widgetPlotToolbar.removeAction(lstActions[7])
        self.vLayout.addWidget(self.mplCanvas)
        self.vLayout.minimumSize() 
        #self.vLayout.addWidget(self.widgetPlotToolbar)
        self.figure.patch.set_visible(False)
        
        
        # and configure matplotlib params
#        rcParams["font.serif"] = "Verdana, Arial, Liberation Serif"
#        rcParams["font.sans-serif"] = "Tahoma, Arial, Liberation Sans"
#        rcParams["font.cursive"] = "Courier New, Arial, Liberation Sans"
#        rcParams["font.fantasy"] = "Comic Sans MS, Arial, Liberation Sans"
#        rcParams["font.monospace"] = "Courier New, Liberation Mono"
#        
        #print self.cbDEM.changeEvent
        self.depth.valueChanged.connect(self.run)
        self.botWidth.valueChanged.connect(self.run)
        self.leftSS.valueChanged.connect(self.run)
        self.rightSS.valueChanged.connect(self.run)
        self.n.valueChanged.connect(self.run)
        self.slope.valueChanged.connect(self.run)
        self.cbWSE.valueChanged.connect(self.run)
        self.ft.clicked.connect(self.run)
        self.m.clicked.connect(self.run)
        self.cbUDwse.valueChanged.connect(self.run)

        self.manageGui() 
     
        self.btnSampleLine.clicked.connect(self.sampleLine)
        self.btnSampleSlope.clicked.connect(self.sampleSlope)



    def manageGui(self):
        print 'manageGui'
        self.cbDEM.clear()
        if utils.getRasterLayerNames():
            self.cbDEM.addItems(utils.getRasterLayerNames())
            self.btnSampleLine.setEnabled(True)
            self.btnSampleSlope.setEnabled(True)           
        self.run()
        
#    def refreshPlot(self):
#        self.axes.clear()

    def plotter(self):

        R, area, topWidth, Q, v, depth, xGround, yGround, yGround0, xWater, yWater, yWater0 = self.args
        self.axes.clear()
        formatter = ScalarFormatter(useOffset=False)
        self.axes.yaxis.set_major_formatter(formatter)
        self.axes.plot(xGround, yGround, 'k')
        #self.axes.fill_between(xGround, yGround, yGround0, where=yGround>yGround0, facecolor='0.9', interpolate=True)
        if Q != 0:
            self.axes.plot(xWater, yWater, 'blue')
            self.axes.fill_between(xWater, yWater, yWater0, where=yWater>=yWater0, facecolor='blue', interpolate=True, alpha = 0.1)
        self.outText = 'R: {0:.2f} {5}\nArea: {1:,.2f} {5}$^2$\nTop Width: {2:.2f} {5}\nDepth: {6:,.2f} {5}\nQ: {3:,.2f} {5}$^3$/s\nVelocity {4:,.2f} {5}/s'.format(R, area, topWidth, Q, v, self.units, depth) 
        self.axes.set_xlabel('Station, '+self.units)
        self.axes.set_ylabel('Elevation, '+self.units)
        self.axes.set_title('Cross Section')
        #self.axes.set_ylim(bottom=0)
        #self.axes.show() 
        
        #print self.outText
        self.refreshPlotText()

    
    def refreshPlotText(self):

        self.axes.annotate(self.outText, xy=(.8,.35), xycoords='figure fraction')
        #at.patch.set_boxstyle("round,pad=0.,rounding_size=0.2")
        #self.axes.add_artist(at)
        self.mplCanvas.draw()
        
    def run(self):
        if self.ft.isChecked():
            self.units = 'ft'
        else:
            self.units = 'm'
            
        if self.tabWidget.currentIndex() == 0:
            print 'calc trap channel'
            self.calcType = 'Trap'
            self.args = flowEstimator(self.depth.value(), self.n.value(), self.slope.value(), widthBottom = self.botWidth.value(), rightSS = self.rightSS.value(), leftSS = self.leftSS.value(), units = self.units)
            self.plotter()
        elif self.tabWidget.currentIndex() == 1:
            try:
                self.calcType = 'DEM'
                self.args = flowEstimator(self.cbWSE.value(), self.n.value(), self.slope.value(), staElev = self.staElev, units = self.units)
                self.plotter()
            except:
                self.axes.clear()
        else:
            
            try:
                self.calcType = 'UD'
                self.args = flowEstimator(self.cbUDwse.value(), self.n.value(), self.slope.value(), staElev = self.staElev, units = self.units)
                self.plotter()
            except:
                self.axes.clear()
                
            
   
    def sampleLine(self):
        try:
            self.deactivate()
        except:
            pass
        self.btnSampleLine.setEnabled(False)  
        self.sampleBtnCode = 'sampleLine'
        self.rubberBand()

 
        
    def sampleSlope(self):
        try:
            self.deactivate()
        except:
            pass
        self.btnSampleSlope.setEnabled(False) 
        self.sampleBtnCode = 'sampleSlope'
        self.rubberBand()
#==============================================================================
# START rubberband and related functions from
#       https://github.com/etiennesky/profiletool
#==============================================================================
    def rubberBand(self):
     
        print 'rubberband ' 
        self.canvas = self.iface.mapCanvas()
        #Init classe variables
        if self.sampleBtnCode=='sampleLine':
            self.tool = ProfiletoolMapTool(self.canvas, self.btnSampleLine)        #the mouselistener
        else:
            self.tool = ProfiletoolMapTool(self.canvas, self.btnSampleSlope)        #the mouselistener
        self.pointstoDraw = None    #Polyline in mapcanvas CRS analysed
        self.dblclktemp = None        #enable disctinction between leftclick and doubleclick
        self.selectionmethod = 0                        #The selection method defined in option
        self.saveTool = self.canvas.mapTool()            #Save the standard mapttool for restoring it at the end
        self.textquit0 = "Click for polyline and double click to end (right click to cancel then quit)"
        self.textquit1 = "Select the polyline in a vector layer (Right click to quit)"
        #Listeners of mouse
        self.connectTool()
        #init the mouse listener comportement and save the classic to restore it on quit
        self.canvas.setMapTool(self.tool)
        #init the temp layer where the polyline is draw
        self.polygon = False
        self.rubberband = QgsRubberBand(self.canvas, self.polygon)
        self.rubberband.setWidth(2)
        if self.sampleBtnCode == 'sampleLine':
            color = Qt.red
        else:
            color = Qt.blue
        self.rubberband.setColor(QColor(color))
        #init the table where is saved the poyline
        self.pointstoDraw = []
        self.pointstoCal = []
        self.lastClicked = [[-9999999999.9,9999999999.9]]
        # The last valid line we drew to create a free-hand profile
        self.lastFreeHandPoints = []
        #Help about what doing
        if self.selectionmethod == 0:
            self.iface.mainWindow().statusBar().showMessage(self.textquit0)
        elif self.selectionmethod == 1:
            self.iface.mainWindow().statusBar().showMessage(self.textquit1)

    #************************************* Mouse listener actions ***********************************************
    
    def moved(self,position):            #draw the polyline on the temp layer (rubberband)
        #print 'moved'
        if self.selectionmethod == 0:
            if len(self.pointstoDraw) > 0:
                #Get mouse coords
                mapPos = self.canvas.getCoordinateTransform().toMapCoordinates(position["x"],position["y"])
                #Draw on temp layer
                if QGis.QGIS_VERSION_INT >= 10900:
                    self.rubberband.reset(QGis.Line)
                else:
                    self.rubberband.reset(self.polygon)
                for i in range(0,len(self.pointstoDraw)):
                     self.rubberband.addPoint(QgsPoint(self.pointstoDraw[i][0],self.pointstoDraw[i][1]))
                self.rubberband.addPoint(QgsPoint(mapPos.x(),mapPos.y()))
#        if self.selectionmethod == 1:
#            return



    def rightClicked(self,position):    #used to quit the current action
        print 'rightclicked'
        if self.selectionmethod == 0:
            if len(self.pointstoDraw) > 0:
                self.pointstoDraw = []
                self.pointstoCal = []
                self.rubberband.reset(self.polygon)
            else:
                self.cleaning()




    def leftClicked(self,position):        #Add point to analyse
        print 'leftclicked'
        mapPos = self.canvas.getCoordinateTransform().toMapCoordinates(position["x"],position["y"])
        newPoints = [[mapPos.x(), mapPos.y()]]
        if self.selectionmethod == 0:
            if newPoints == self.dblclktemp:
                self.dblclktemp = None
                return
            else :
                if len(self.pointstoDraw) == 0:
                    self.rubberband.reset(self.polygon)
                self.pointstoDraw += newPoints


    def doubleClicked(self,position):
        print 'doubleclicked'
        if self.selectionmethod == 0:
            #Validation of line
            mapPos = self.canvas.getCoordinateTransform().toMapCoordinates(position["x"],position["y"])
            newPoints = [[mapPos.x(), mapPos.y()]]
            self.pointstoDraw += newPoints
            #launch analyses
            self.iface.mainWindow().statusBar().showMessage(str(self.pointstoDraw))
            
            if self.sampleBtnCode == 'sampleLine':
                self.staElev, error = self.doRubberbandProfile()
                if error:
                    self.deactivate()
                else:
                    self.doIrregularProfileFlowEstimator()
                self.btnSampleLine.setEnabled(True) 
                self.deactivate()
            else:
                staElev, error = self.doRubberbandProfile()
                if error:
                    self.deactivate()
                else:
                    self.doRubberbandSlopeEstimator(staElev)     
                self.btnSampleSlope.setEnabled(True) 
                self.deactivate()

            #Reset
            self.lastFreeHandPoints = self.pointstoDraw
            self.pointstoDraw = []
            #temp point to distinct leftclick and dbleclick
            self.dblclktemp = newPoints
            self.iface.mainWindow().statusBar().showMessage(self.textquit0)
            self.iface.mainWindow().activateWindow()
            return


###***********************************************
            
    def connectTool(self):
        print 'connecting'
        QObject.connect(self.tool, SIGNAL("moved"), self.moved)
#        self.tool.moved.connect(self.moved)
        QObject.connect(self.tool, SIGNAL("rightClicked"), self.rightClicked)
        QObject.connect(self.tool, SIGNAL("leftClicked"), self.leftClicked)
        QObject.connect(self.tool, SIGNAL("doubleClicked"), self.doubleClicked)
        QObject.connect(self.tool, SIGNAL("deactivate"), self.deactivate)

    def deactivate(self):        #enable clean exit of the plugin
        self.cleaning()
        QObject.disconnect(self.tool, SIGNAL("moved"), self.moved)
        QObject.disconnect(self.tool, SIGNAL("leftClicked"), self.leftClicked)
        QObject.disconnect(self.tool, SIGNAL("rightClicked"), self.rightClicked)
        QObject.disconnect(self.tool, SIGNAL("doubleClicked"), self.doubleClicked)
#        self.rubberband.reset(self.polygon)
#        self.iface.mainWindow().statusBar().showMessage("")
        
#        self.depth.setEnabled(True)
#        self.botWidth.setEnabled(True)
#        self.leftSS.setEnabled(True)
#        self.rightSS.setEnabled(True)
#        self.n.setEnabled(True)
#        self.slope.setEnabled(True)
#        self.cbWSE.setEnabled(True)
#        self.ft.setEnabled(True)
#        self.m.setEnabled(True)
#        self.cbDEM.setEnabled(True)

    def cleaning(self):            #used on right click
        self.canvas.unsetMapTool(self.tool)
        self.canvas.setMapTool(self.saveTool)
        self.rubberband.reset(self.polygon)
        #self.rubberband.reset(self.polygon)
        self.iface.mainWindow().statusBar().showMessage( "" )
#==============================================================================
# END rubberband and related functions from
#       https://github.com/etiennesky/profiletool
#==============================================================================
    
    def doRubberbandProfile(self):
        layerString = self.cbDEM.currentText()
        layer = utils.getRasterLayerByName(' '.join(layerString.split(' ')[:-1]))
        if layer.isValid():
            self.xRes = layer.rasterUnitsPerPixelX()
        line = LineString(self.pointstoDraw[:-1]) 
        xyzdList = utils.elevationSampler(line,self.xRes, layer)
        sta = xyzdList[-1]
        elev = xyzdList[-2]
        staElev = np.array(zip(sta, elev))
        try:
            np.isnan(np.sum(staElev[:,1]))
            return [staElev, None]
        except:
            QMessageBox.warning(self,'Error',
                                'Sampled line not within bounds of DEM')
            #self.cleaning()
            
            return [staElev, 'error']
            
            
        
    def doIrregularProfileFlowEstimator(self):
        thalweig = self.staElev[np.where(self.staElev[:,1] == np.min(self.staElev[:,1]))] 
        thalweigX = thalweig[:,0][0]
        minElev = thalweig[:,1][0]+.01
        try:
            lbMaxEl = self.staElev[np.where(self.staElev[:,0]>thalweigX)][:,1].max()
        except:
            QMessageBox.warning(self,'Error', 'Channel not found')
            try:
                self.deactivate()
            except:
                pass
            return
        try:
            rbMaxEl = self.staElev[np.where(self.staElev[:,0]<thalweigX)][:,1].max()
        except:
            QMessageBox.warning(self,'Error', 'Channel not found')
            try:
                self.deactivate()
            except:
                pass
            return 
        maxElev = np.array([lbMaxEl,rbMaxEl]).min()-.01
        WSE = maxElev
        #WSE = (self.staElev[:,1].max() - self.staElev[:,1].min())/2. + self.staElev[:,1].min()
        if self.tabWidget.currentIndex() == 1:
            self.cbWSE.setValue(WSE)
            self.cbWSE.setMinimum(minElev)
            self.cbWSE.setMaximum(maxElev)
        elif self.tabWidget.currentIndex() == 2:
            self.cbUDwse.setValue(WSE)
            self.cbUDwse.setMinimum(minElev)
            self.cbUDwse.setMaximum(maxElev)
        else:
            return

        self.run()

        
    def doRubberbandSlopeEstimator(self, staElev):
         
        slope = -(staElev[:,1][-1] - staElev[:,1][0])/staElev[:,0][-1]
        print slope

        self.axes.clear()
        
        formatter = ScalarFormatter(useOffset=False)
        self.axes.yaxis.set_major_formatter(formatter)
        self.axes.plot(staElev[:,0],staElev[:,1], 'k',label = 'Sampled DEM')
        x = np.array([staElev[0,0], staElev[-1,0]])
        y = np.array([staElev[0,1], staElev[-1,1]])
        self.axes.plot(x,y, label = 'Slope')
        self.axes.set_xlabel('Station, '+self.units)
        self.axes.set_ylabel('Elevation, '+self.units)
        self.axes.set_title('DEM Derived Slope = '+slope.astype('|S8'))
        self.axes.legend()
        self.mplCanvas.draw()
        if slope<=0:
            QMessageBox.warning(self,'Error',
                                'Negative or zero slope\nPlease check sampled area\n\nWater flows downhill you know!')
            print 'error: negative slope'
        else:
            reply = QMessageBox.question(self,'Message',
            'DEM Derived Slope is {}\nWould you like to use this value?'.format(slope.astype('|S8')), QMessageBox.Yes| 
            QMessageBox.No, QMessageBox.Yes)
            if reply == QMessageBox.Yes:
                self.slope.setValue(slope)

            else:
                pass
            
    def writeDirName(self):
        self.outputDir.clear()
        self.dirName = QFileDialog.getExistingDirectory(self, 'Select Output Directory')
        self.outputDir.setText(self.dirName)
        
    def loadTxt(self):
        filePath = QFileDialog.getOpenFileName(self, 'Select tab or space delimited text file containing station and elevation data')
        print filePath
        try:
            self.staElev = np.loadtxt(filePath)
            self.inputFile.setText(filePath)
            self.calcType = 'UD' 
            self.doIrregularProfileFlowEstimator()
        except:
            QMessageBox.warning(self,'Error',
                                'Please check that the text file is space or tab delimited and does not contain header information')
        
        
    def accept(self):
        # assign results to numpy array for quick csv dump
        outPath = self.outputDir.text()
        home = os.path.expanduser("~")
        if outPath == '':
            outPath = os.path.join(home,'Desktop','QGIS2FlowEstimatorFiles')
            self.outputDir.setText(outPath)
            if not os.path.exists(outPath):
                os.makedirs(outPath)             
        os.chdir(outPath)
        fileName = 'FlowEstimatorResults.txt'
        outFile = open(fileName,'w') 
        outHeader = '*'*20 + '\nFlow Estimator - A QGIS plugin\nEstimates uniform, steady flow in a channel using Mannings equation\n' + '*'*20
        if self.calcType == 'DEM':
             proj4 = utils.getRasterLayerByName(self.cbDEM.currentText().split(' EPSG')[0]).crs().toProj4()
             outHeader += '\n'*5 + 'Type:\tCross Section from DEM\nUnits:\t{0}\nDEM Layer:\t{1}\nProjection (Proj4 format):\t{2}\nChannel Slope:\t{3:.06f}\nMannings n:\t{4:.02f}\n\n\n\nstation\televation\n'.format(self.units,self.cbDEM.currentText(), proj4, self.slope.value(), self.n.value())
             outFile.write(outHeader)
             np.savetxt(outFile, self.staElev, fmt = '%.3f', delimiter = '\t')
             wseMax = self.cbWSE.value()
             wseMin = self.cbWSE.minimum()
        elif self.calcType =='UD':
             proj4 = utils.getRasterLayerByName(self.cbDEM.currentText().split(' EPSG')[0]).crs().toProj4()
             outHeader += '\n'*5 + 'Type:\tUser Defined Cross Section\nUnits:\t{0}\nChannel Slope:\t{1:.06f}\nMannings n:\t{2:.02f}\n\n\n\nstation\televation\n'.format(self.units, self.slope.value(), self.n.value())
             outFile.write(outHeader)
             np.savetxt(outFile, self.staElev, fmt = '%.3f', delimiter = '\t')
             wseMax = self.cbUDwse.value()
             wseMin = self.cbUDwse.minimum()            
            
        else:
            outHeader += '\n'*5 + 'Type:\tTrapizodal Channel\nUnits:\t{0}\nChannel Slope:\t{1:.06f}\nMannings n:\t{2:.02f}\nBottom Width:\t{3:.02f}\nRight Side Slope:\t{4:.02f}\nLeft Side Slope:\t{5:.02f}\n'.format(self.units, self.slope.value(), self.n.value(), self.botWidth.value(), self.rightSS.value(), self.leftSS.value())
            outFile.write(outHeader)
            wseMax = self.depth.value()
            wseMin = 0.0
        self.mplCanvas.print_figure('FlowEstimatorResultsXSFigure')
        outHeader = '\n\n\n\n\n\n\nwater surface elevation\tflow\tvelocity\tR\tarea\ttop width\tdepth\n'
        outFile.write(outHeader)
        ###do loop here 
        step = 0.1
        wseList = []
        qList = []
        for wse in utils.frange(wseMin, wseMax, step):
            if self.calcType == 'DEM' or self.calcType == 'UD':
                args = flowEstimator(wse, self.n.value(), self.slope.value(), staElev = self.staElev, units = self.units)
            else:
                args = flowEstimator(wse, self.n.value(), self.slope.value(), widthBottom = self.botWidth.value(), rightSS = self.rightSS.value(), leftSS = self.leftSS.value(), units = self.units)
            R, area, topWidth, Q, v, depth, xGround, yGround, yGround0, xWater, yWater, yWater0 = args
            data = '{0}\t{1:.02f}\t{2:.02f}\t{3:.02f}\t{4:.02f}\t{5:.02f}\t{6:.02f}\n'.format(wse, Q, v, R, area, topWidth, depth)
            outFile.write(data)
            wseList.append(wse)
            qList.append(Q)
            
        self.axes.clear()
        formatter = ScalarFormatter(useOffset=False)
        self.axes.yaxis.set_major_formatter(formatter)
        self.axes.plot(qList, wseList, 'k',label = 'Rating Curve')
        self.axes.set_ylabel('Water Surface Elevation, '+self.units)
        self.axes.set_xlabel('Discharge, {0}$^3$/s'.format(self.units))
        self.axes.set_title('Rating Curve')
        self.axes.grid()
        self.mplCanvas.draw()
        self.mplCanvas.print_figure('FlowEstimatorRatingCurve')          
        
        
        outFile.close()
        
        self.iface.messageBar().pushMessage("Flow Estimator", 'Output files located here {}.  Please delete when finished'.format(outPath),duration=30)

