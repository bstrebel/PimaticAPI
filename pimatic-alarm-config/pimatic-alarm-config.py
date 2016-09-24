#!/usr/bin/env python
# -*- coding: utf-8 -*-

from __future__ import absolute_import
from __future__ import print_function

import os, sys, uuid, logging, logging.config, json, codecs, time, pyutils

from pyutils import Options, LogAdapter, strflocal, get_logger, log_level
from pimatic import PimaticAPI

def main():

    from argparse import ArgumentParser
    from pimatic import __version__, __author__

    options = {
        'secrets': '~/.pysync.secrets',
        'loglevel_requests': 'ERROR'
        #'loglevel': 'INFO'
    }

# region Command line arguments

    parser = ArgumentParser(description='pimatic-alarm-config [PimaticAPI Rev. %s (c) %s]' % (__version__, __author__))
    parser.add_argument('-c', '--config', type=str, help='use alternate configuration file(s)')

    parser.add_argument('--relations', type=str, help='list of pysync relations to process')
    parser.add_argument('--rebuild', action='store_true', help='rebuild map file')
    parser.add_argument('--reset', type=str, help='delete entries and recreate from left/right')
    parser.add_argument('--update', type=str, help='force update on left/right side')

    parser.add_argument('-l', '--loglevel', type=str,
                        choices=['DEBUG', 'INFO', 'WARNING', 'ERROR', 'CRITICAL'],
                        help='debug log level')

    args = parser.parse_args()

    opts = Options(options, args, '[config]', prefix='PYSYNC')
    config = opts.config_parser

    if config is None:
        LogAdapter(get_logger(), {'package': 'main'}).critical("Missing configuration file!")
        exit(1)

    logger = LogAdapter(opts.logger, {'package': 'main'})
# endregion
