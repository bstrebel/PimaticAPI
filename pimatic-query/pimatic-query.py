#!/usr/bin/env python
# -*- coding: utf-8 -*-

from __future__ import absolute_import
from __future__ import print_function

import os, sys, uuid, logging, logging.config, json, codecs, time, datetime, pyutils, urllib

from pyutils import Options, LogAdapter, strflocal, get_logger, log_level
from pimatic import PimaticAPI

# development environment with local secrets
try:
    from private import *
except ImportError:
    pass

devices = {}

def check_result(result, key):
    if result is not None and result.get(key) is not None:
        return True
    return False

with PimaticAPI(server=PIMATIC_SERVER,
                username=PIMATIC_USERNAME,
                password=PIMATIC_PASSWORD) as pimatic:

    pimatic.login()

    result = pimatic.get('/api/devices')
    if check_result(result,'devices'):
        for device in result['devices']:
            devices[device['id']] = device

    for id in devices:
        print(id)

    after_spec = "2016-09-18 09:51:04"
    after_stamp = int(time.mktime(datetime.datetime.strptime(after_spec,"%Y-%m-%d %H:%M:%S").timetuple())) * 1000

    criteria = {'criteria[deviceId]': 'switch_alarm_prealert',
                'criteria[orderDirection]':'DESC]',
                'criteria[after]': after_stamp}

    result = pimatic.get('/api/database/device-attributes/?' + urllib.urlencode(criteria))
    if check_result(result,'events'):
        for event in result['events']:
            print(strflocal(event['time']), event['time'], event['value'])
