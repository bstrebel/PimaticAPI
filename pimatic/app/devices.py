#!/usr/bin/env python
# -*- coding: utf-8 -*-

from __future__ import absolute_import
from __future__ import print_function

import os, sys, re, uuid, logging, logging.config, json, codecs, time, datetime, urllib

from pyutils import Options, LogAdapter, strflocal, localfstr, get_logger, log_level, utf8, string
from pimatic.app import PimaticApp

class PimaticDevicesApp(PimaticApp):

    options = {
        'app': 'PimaticDevicesApp',
        'rev': '0.9.5',
        'config': '~/.pimatic/pimatic.cfg,~/.pimatic/devices.cfg',
        'device': '.*',
        'loglevel_requests': 'ERROR',
        'loglevel': 'DEBUG'
    }

    def __init__(self):

        super(PimaticDevicesApp, self).__init__(self.options)

        # device only options
        self._parser.add_argument('-d', '--device', type=str, help='device specification (regex)')
        self._parser.add_argument('-v', '--invert', action='store_true', help='invert regex match')
        self._parser.add_argument('-x', '--exclude', type=str, help='device specification (regex)')

        self._parser.add_argument('-f', '--format', type=str, choices=['JSON', 'LIST'], help='output format')
        self._parser.add_argument('-o', '--order', type=str, help='order by attribute')
        self._parser.add_argument('-r', '--reverse', action='store_true', help='reverse sort order')

        self.parse()

    def run(self):

        opts = self._opts
        logger = self._logger

        session = self.session()

        with self._pimatic as pimatic:

            pattern = None
            exclude = None

            if opts.device:
                pattern = re.compile(opts.device)
                logger.info(u'device: %s' % (opts.device))
                logger.info(u'invert: %s' % (opts.invert))

            if opts.exclude:
                exclude = re.compile(opts.exclude)
                logger.info(u'exclude: %s' % (opts.exclude))

            inverse = opts.invert

            width = {'id': 0, 'name': 0, 'cname': 0}
            devices = []

            def devices_append(id):
                device = pimatic.devices[id]
                device['cname'] = device['config']['class']
                for k in width:
                    width[k] = max(width[k], len(device[k]))
                devices.append(id)

            for id in pimatic.devices:
                if exclude is not None:
                    if not exclude.search(id):
                        if pattern is not None:
                            if inverse:
                                if not pattern.search(id): devices_append(id)
                            else:
                                if pattern.search(id): devices_append(id)
                        else:
                            devices_append(id)
            devices.sort()
            logger.info(u'devices: %d (%d)' % (len(devices), len(pimatic.devices)))

            for id in devices:
                device = pimatic.devices[id]
                short = u'{:{id}} {:{name}} {:{cname}}'.format(device['id'],
                                                               device['name'],
                                                               device['cname'],
                                                               id=width['id'], name=width['name'], cname=width['cname'])
                print(string(short))


# region __Main__
def main():
    return PimaticDevicesApp().run()

if __name__ == '__main__':
    exit(main())
# endregion
