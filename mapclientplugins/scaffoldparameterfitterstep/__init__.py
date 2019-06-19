
"""
MAP Client Plugin
"""

__version__ = '0.1.0'
__author__ = 'Mahyar Osanlouy'
__stepname__ = 'Scaffold Parameter Fitter'
__location__ = ''

# import class that derives itself from the step mountpoint.
from mapclientplugins.scaffoldparameterfitterstep import step

# Import the resource file when the module is loaded,
# this enables the framework to use the step icon.
from . import resources_rc