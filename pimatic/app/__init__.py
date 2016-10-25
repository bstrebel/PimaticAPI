import os

__version__ = '0.9.4'
__license__ = 'GPL2'
__author__ = 'Bernd Strebel'

PACKAGE_DIR = os.path.dirname(os.path.abspath(__file__))

from .core import PimaticApp

__all__ = [

    'PimaticApp'
]
