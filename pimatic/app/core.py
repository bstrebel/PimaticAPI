#!/usr/bin/env python
# -*- coding: utf-8 -*-

from __future__ import absolute_import
from __future__ import print_function

import os, sys, re, uuid, logging, logging.config, json, codecs, time, datetime, urllib
from collections import OrderedDict

from pyutils import Options, LogAdapter, strflocal, localfstr, get_logger, log_level
from pimatic import PimaticAPI

from ConfigParser import ConfigParser
from argparse import ArgumentParser
from pimatic import __version__, __author__

class PimaticApp(object):

    def __init__(self, options):

        self._options = options

        self._pimatic = None
        self._args = None
        self._opts = None
        self._config = None
        self._logger = None

        self._node = {'url': None, 'username': None, 'password': None}

        self._parser = ArgumentParser(description='%s [PimaticAPI Rev. %s (c) %s]' % (self.app, __version__, __author__))

        self._parser.add_argument('-c', '--config', type=str, help='use alternate configuration file(s)')
        self._parser.add_argument('-s', '--secrets', type=str, help='use alternate secrets file(s)')
        self._parser.add_argument('-l', '--loglevel', type=str, choices=['DEBUG', 'INFO', 'WARNING', 'ERROR', 'CRITICAL'],
                                   help='debug log level')

        self._parser.add_argument('-n', '--node', type=str, help='pimatic node instance')
        self._parser.add_argument('-u', '--username', type=str, help='pimatic username')
        self._parser.add_argument('-p', '--password', type=str, help='pimatic password')


    def parse(self):

        self._args = self._parser.parse_args()
        self._opts = Options(self._options, self._args, '[config]', prefix='PIMATIC')
        self._config = self._opts.config_parser

        if self._config is None:
            LogAdapter(get_logger(), {'package': self.app}).critical("Missing configuration file!")
            exit(1)

        self._logger = LogAdapter(self._opts.logger, {'package': self.app})

# region Get node configuration and logger settings

        # set log level of requests module
        logging.getLogger('requests').setLevel(log_level(self._opts.loglevel_requests))
        logging.getLogger('urllib3').setLevel(log_level(self._opts.loglevel_requests))

        self._logger.debug(u'Parsing configuration file %s' % (self._opts.config_file))

        if self._config.has_option('options', 'secrets'):
            secrets = self._config.get('options', 'secrets')
            path = os.path.expanduser(secrets)
            if os.path.isfile(path):
                secret = ConfigParser()
                secret.read(path)

        if self._opts.node:
            if self._opts.node.startswith('http'):
                self._node['url'] = self._opts.node
            else:
                node_section = 'node_' + self._opts.node
                if secret.has_section(node_section):
                    protocol = secret.get(node_section, 'protocol')
                    server = secret.get(node_section, 'server')
                    port = secret.get(node_section, protocol + '_port')
                    self._node['url']=protocol + '://' + server + ':' + port
                    self._node['username'] = secret.get(node_section, 'username')
                    self._node['password'] = secret.get(node_section, 'password')
                else:
                    self._logger.critical(u'Invalid node tag %s' % (node_section))
                    exit(1)
        else:
            self._logger.critical(u'Missing pimatic node specification!')
            exit(1)

        if self._opts.username:
            self._node['username'] = self._opts.username

        if self._opts.password:
            self._node['password'] = self._opts.password

# endregion

        self._logger.info(u'url: %s' % (self._node['url']))

    def session(self):

        self._pimatic = PimaticAPI(server=self._node['url'],
                                   username=self._node['username'],
                                   password=self._node['password'],
                                   logger=self._logger)
        return self._pimatic

    @property
    def app(self): return self._options.get('app')

# region __Main__
if __name__ == '__main__':
    exit(0)
# endregion
