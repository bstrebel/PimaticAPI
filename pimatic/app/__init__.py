import os

PACKAGE_DIR = os.path.dirname(os.path.abspath(__file__))

from .core import PimaticApp

__all__ = [

    'PimaticApp'
]
