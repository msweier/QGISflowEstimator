# -*- coding: utf-8 -*-
"""
/***************************************************************************
 FlowEstimator
                                 A QGIS plugin
 Estimates steady, uniform flow using the Manning equation for trapezoidal and DEM sampled channels.
                             -------------------
        begin                : 2015-05-21
        copyright            : (C) 2015 by M. Weier - North Dakota State Water Commision
        email                : mweier@nd.gov
        git sha              : $Format:%H$
 ***************************************************************************/

/***************************************************************************
 *                                                                         *
 *   This program is free software; you can redistribute it and/or modify  *
 *   it under the terms of the GNU General Public License as published by  *
 *   the Free Software Foundation; either version 2 of the License, or     *
 *   (at your option) any later version.                                   *
 *                                                                         *
 ***************************************************************************/
 This script initializes the plugin, making it known to QGIS.
"""


# noinspection PyPep8Naming
def classFactory(iface):  # pylint: disable=invalid-name
    """Load FlowEstimator class from file FlowEstimator.

    :param iface: A QGIS interface instance.
    :type iface: QgsInterface
    """
    #
    from .flow_estimator import FlowEstimator
    return FlowEstimator(iface)
