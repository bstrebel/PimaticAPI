#!/usr/bin/env python
# -*- coding: utf-8 -*-

from __future__ import absolute_import
from __future__ import print_function

import os, sys, re, uuid, logging, logging.config, json, codecs, time, datetime, urllib

from pyutils import Options, LogAdapter, strflocal, localfstr, get_logger, log_level, utf8, string
from pimatic.app import PimaticApp

class PimaticAlarmShutterApp(PimaticApp):

    options = {
        'app': 'PimaticAlarmShutterApp',
        'rev': '0.9.6',
        'config': '~/.pimatic/pimatic.cfg,~/.pimatic/alarm.cfg',
        'state': 'disabled',
        'loglevel_requests': 'ERROR',
        'loglevel': 'DEBUG'
    }

    def __init__(self):

        super(PimaticAlarmShutterApp, self).__init__(self.options)
        self._parser.add_argument('state', nargs='?', default='disabled')
        self.parse()

    def run(self):

        opts = self._opts
        logger = self._logger

        shutters = opts.shutter.split(',')
        logger.debug(u'Shutter alarm [{}] for [{}]'.format(self._args.state, opts.shutter))

        session = self.session()

        with self._pimatic as pimatic:

            for shutter in shutters:
                deviceId = 'contact_shutter_' + shutter
                contact = pimatic.devices.get(deviceId)
                if contact:
                    closed = contact[u'attributes'][0]['value']
                    ruleId = u'rule_alarm-alert-shutter-{}'.format(shutter)
                    rule = pimatic.rules.get(ruleId)
                    if rule:
                        active = (closed and (self._args.state.lower() == 'enabled'))
                        if rule['active'] != active:
                            result = pimatic.patch('/api/rules/{}'.format(ruleId), {"rule": {"active": active}})
                            if not result:
                                logger.critical(u'Error patching rule [{}]'.format(ruleId))
                                exit(4)
                            else:
                                logger.info(u'Shutter device [{}] changed to [{}]'.format(deviceId, self._args.state))
                        else:
                            logger.debug(u'Shutter device [{}] already [{}]'.format(deviceId, self._args.state))
                    else:
                        logger.critical(u'Missung rule [{}]'.format(ruleId))
                        exit(3)
                else:
                    logger.critical(u'Missung device [{}]'.format(deviceId))
                    exit(2)

# region __Main__
def main():
    return PimaticAlarmShutterApp().run()

if __name__ == '__main__':
    exit(main())
# endregion
