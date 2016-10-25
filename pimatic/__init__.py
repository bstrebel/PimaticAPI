import os

__version__ = '0.9.5'
__license__ = 'GPL2'
__author__ = 'Bernd Strebel'

PACKAGE_DIR = os.path.dirname(os.path.abspath(__file__))

from .session import PimaticAPI

__all__ = [

    'PimaticAPI'
]
