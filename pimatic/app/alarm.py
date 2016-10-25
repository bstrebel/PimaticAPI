#!/usr/bin/env python
# -*- coding: utf-8 -*-

from __future__ import absolute_import
from __future__ import print_function

import os, sys, re, uuid, logging, logging.config, json, codecs, time, datetime, urllib

from pyutils import Options, LogAdapter, strflocal, localfstr, get_logger, log_level, utf8, string
from pimatic.app import PimaticApp

class PimaticAlarmConfigApp(PimaticApp):

    options = {
        'app': 'PimaticAlarmConfigApp',
        'config': '~/.pimatic/pimatic.cfg,~/.pimatic/alarm.cfg',
        'profile': 'default',
        'loglevel_requests': 'ERROR',
        'loglevel': 'DEBUG'
    }

    def __init__(self):

        super(PimaticAlarmConfigApp, self).__init__(self.options)
        self._parser.add_argument('profile', nargs='?', default='default')
        self.parse()

    def run(self):

        opts = self._opts
        logger = self._logger

        contacts = None
        section = None

        if self._config.has_section('profile_' + self._args.profile):

            section = 'profile_' + self._args.profile
            contacts = opts.keys(section)
        else:
            logger.critical(u'Profile [{}] not found!'.format(self._args.profile))
            exit(1)

        logger.info(u'Profile [{}] requested'.format(self._args.profile))

        session = self.session()

        with self._pimatic as pimatic:

            # turn off alarm system
            result = pimatic.get(u'/api/device/{}/turnOff'.format(opts.switch))
            if not result:
                logger.critical(u'Cannot switch [{}] off!'.format(opts.switch))
                exit(2)

            logger.debug(u'Device [{}] switched off'.format(opts.switch))

            if not pimatic.rules.get(opts.check):
                logger.critical(u'Rule [{}] not found!'.format(opts.check))
                exit(3)

            rule_string = pimatic.rules.get(opts.check)['string']
            logger.debug(u'{}: {}'.format(opts.check, rule_string))

            if '[' in rule_string:
                rule_when, rest = rule_string.split('[')
                rest, rule_then = rule_string.split(']')
            else:
                m = re.match('(.* pressed and if )(.*)( then .*)', rule_string)
                rule_when, rest, rule_then = m.groups()

            rule_condition = u''

            if pimatic.variable('alarmProfile', u'undefined') is None:
                logger.critical(u'Error patching [$alarmProfile]')
                exit(4)

            alarmLocked = pimatic.variable('alarmLocked')
            alarmLockedDevice = pimatic.variable('alarmLockedDevice')

            if pimatic.variable('alarmLocked', 1) is None:
                logger.critical(u'Error patching [alarmLocked]')
                exit(5)

            if pimatic.variable('alarmLockedDevice', u'') is None:
                logger.critical(u'Error patching [$alarmLockedDevice]')
                exit(5)

            # create temporary alarm check rule: prevent alarm system activation if profile is "undefined"
            rule_button = rule_when.split()[1]
            rule_undefined = u'when {} is pressed and if [$alarmProfile = "undefined"] then set $alarmLocked = 1'.format(
                rule_button)
            result = pimatic.patch('/api/rules/{}'.format(opts.check), {"rule": {"ruleString": rule_undefined}})
            if not result:
                logger.critical(u'Error patching [{}]'.format(opts.check))
                exit(7)

            devices = []

            for contact in contacts:

                state = self._config.getboolean(section, contact)

                logger.info(u'{}: {}'.format(contact, state))

                # device name magic ...
                device = contact.replace('contact_', '')
                if state:
                    devices.append(device)
                device = device.replace('_', '-')
                for prefix in ['alert', 'locked', 'unlock']:
                    rule = u'rule_alarm-{}-{}'.format(prefix, device)
                    if pimatic.rules.get(rule):
                        if pimatic.rules.get(rule)['active'] != state:
                            result = pimatic.patch('/api/rules/{}'.format(rule), {"rule": {"active": state}})
                            if not result:
                                logger.critical(u'Error patching rule [{}]'.format(rule))
                                exit(5)
                    else:
                        logger.critical(u'Missung rule [{}]'.format(rule))
                        exit(6)

                if state:
                    rule_condition = rule_condition + contact + u' is closed and '

            devices.sort()

            rule_condition = rule_condition[:-5]
            rule_string = u'{}[{}]{}'.format(rule_when, rule_condition, rule_then)

            # logger.debug(u'{}: {}'.format(opts.check, rule_string))

            result = pimatic.patch('/api/rules/{}'.format(opts.check), {"rule": {"ruleString": rule_string}})
            if not result:
                logger.critical(u'Error patching [{}]'.format(opts.check))
                exit(7)

            pimatic.variable('alarmProfile', self._args.profile)

            if pimatic.variable('alarmLocked', alarmLocked) is None:
                logger.critical(u'Error patching [alarmLocked]')
                exit(8)

            if pimatic.variable('alarmLockedDevice', alarmLockedDevice) is None:
                logger.critical(u'Error patching [$alarmLockedDevice]')
                exit(9)

            print('{}: {}'.format(self._args.profile, devices))
            logger.info(u'Profile [{}] activated'.format(self._args.profile))


# region __Main__
def main():
    return PimaticAlarmConfigApp().run()

if __name__ == '__main__':
    exit(main())
# endregion
