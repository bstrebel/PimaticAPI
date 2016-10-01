#!/usr/bin/env python
# -*- coding: utf-8 -*-

from __future__ import absolute_import
from __future__ import print_function

import os, sys, re, uuid, logging, logging.config, json, codecs, time, datetime, urllib

from pyutils import Options, LogAdapter, strflocal, localfstr, get_logger, log_level
from pimatic import PimaticAPI

def main():

    from ConfigParser import ConfigParser
    from argparse import ArgumentParser
    from pimatic import __version__, __author__

    node = {'url': None, 'username': None, 'password': None}

    options = {
        'config': '~/.pimatic/pimatic.cfg',
        'window': '90s',
        'device': '.*',
        'exclude': '(var_|weather|sunrise|forecast|bmp|syssensor)',
        'format': '%Y-%d-%m %H:%M:%S',
        'loglevel_requests': 'ERROR',
        'loglevel': 'DEBUG'
    }

# region Command line arguments

    parser = ArgumentParser(description='pimatic-query [PimaticAPI Rev. %s (c) %s]' % (__version__, __author__))

    parser.add_argument('-c', '--config', type=str, help='use alternate configuration file(s)')
    parser.add_argument('-s', '--secrets', type=str, help='use alternate secrets file(s)')
    parser.add_argument('-l', '--loglevel', type=str, choices=['DEBUG', 'INFO', 'WARNING', 'ERROR', 'CRITICAL'],
                        help='debug log level')

    parser.add_argument('-n', '--node', type=str, help='pimatic node instance')
    parser.add_argument('-u', '--username', type=str, help='pimatic username')
    parser.add_argument('-p', '--password', type=str, help='pimatic password')

    parser.add_argument('-d', '--device', type=str, help='device specification (regex)')
    parser.add_argument('-v', '--invert', action='store_true', help='invert regex match')
    parser.add_argument('-x', '--exclude', type=str, help='device specification (regex)')
    parser.add_argument('-a', '--after', type=str, help='after datetime')
    parser.add_argument('-b', '--before', type=str, help='before datetime')
    parser.add_argument('-t', '--time', type=str, help='datetime spec ')
    parser.add_argument('-w', '--window', type=str, help='time window')
    parser.add_argument('-o', '--order', type=str, help='order by attribute (default: time)')
    parser.add_argument('-r', '--reverse', action='store_true', help='reverse sort order')
    # parser.add_argument('-f', '--offset', type=str, help='offset')
    # parser.add_argument('-l', '--limit', type=str, help='limit')

    args = parser.parse_args()
    opts = Options(options, args, '[config]', prefix='PIMATIC')
    config = opts.config_parser

    if config is None:
        LogAdapter(get_logger(), {'package': 'pimatic-query'}).critical("Missing configuration file!")
        exit(1)

    logger = LogAdapter(opts.logger, {'package': 'pimatic-query'})

# endregion

# region Get node configuration and logger settings

    # set log level of requests module
    logging.getLogger('requests').setLevel(log_level(opts.loglevel_requests))
    logging.getLogger('urllib3').setLevel(log_level(opts.loglevel_requests))

    logger.debug(u'Parsing configuration file %s' % (opts.config_file))

    if config.has_option('options', 'secrets'):
        secrets = config.get('options', 'secrets')
        path = os.path.expanduser(secrets)
        if os.path.isfile(path):
            secret = ConfigParser()
            secret.read(path)

    if config.has_section('alarmsystem'):
        pass

    if opts.node:
        if opts.node.startswith('http'):
            node['url']=opts.node
        else:
            node_section = 'node_' + opts.node
            if secret.has_section(node_section):
                protocol = secret.get(node_section, 'protocol')
                server = secret.get(node_section, 'server')
                port = secret.get(node_section, protocol + '_port')
                node['url']=protocol + '://' + server + ':' + port
                node['username'] = secret.get(node_section, 'username')
                node['password'] = secret.get(node_section, 'password')
            else:
                logger.critical(u'Invalid node tag %s' % (node_section))
                exit(1)
    else:
        logger.critical(u'Missing pimatic node specification!')
        exit(1)

    if opts.username:
        node['username'] = opts.username

    if opts.password:
        node['password'] = opts.password

# endregion

    logger.info(u'url: %s' % (node['url']))

    with PimaticAPI(server=node['url'],
                    username=node['username'],
                    password=node['password'],
                    logger=logger) as pimatic:

        pass
