#!/usr/bin/env python
# -*- coding: utf-8 -*-

from __future__ import absolute_import
from __future__ import print_function

import os, sys, re, uuid, logging, logging.config, json, codecs, time, datetime, urllib

from pyutils import Options, LogAdapter, strflocal, localfstr, get_logger, log_level
from pimatic import PimaticAPI

def filter(session, logger, device, invert, exclude):

    # generate device list
    pattern = None
    exclude = None
    if device:
        pattern = re.compile(device)
        logger.info(u'device: %s' % (device))
        logger.info(u'invert: %s' % (invert))
    if exclude:
        exclude = re.compile(exclude)
        logger.info(u'exclude: %s' % (exclude))
    inverse = invert
    devices = []
    for id in session.devices:
        if exclude is not None:
            if not exclude.search(id):
                if pattern is not None:
                    if inverse:
                        if not pattern.search(id): devices.append(id)
                    else:
                        if pattern.search(id): devices.append(id)
                else:
                    devices.append(id)
    devices.sort()
    logger.info(u'devices: %d (%d)' % (len(devices), len(session.devices)))
    # for id in devices: print(id)
    return devices
