from setuptools import setup
import re

version = re.search(
    "^__version__\s*=\s*'(.*)'",
    open('pimatic/__init__.py').read(),
    re.M).group(1)

setup(
    name='PimaticAPI',
    version=version,
    packages=['pimatic','pimatic.app'],
    url='https://github.com/bstrebel/PimaticAPI',
    license='GPL2',
    author='Bernd Strebel',
    author_email='b.strebel@digitec.de',
    description='Python PimaticAPI',
    long_description=open('README.md').read(),
    install_requires=['PyUtils>=0.5.0'],
    entry_points={'console_scripts': ['pimatic-events = pimatic.app.events:main',
                                      'pimatic-devices = pimatic.app.devices:main',
                                      'pimatic-alarm = pimatic.app.alarm:main',
                                      'pimatic-shutter = pimatic.app.shutter:main']}
)
