#!/usr/bin/env python
# -*- coding: utf-8 -*-

from __future__ import absolute_import
from __future__ import print_function

import os, sys, re, uuid, logging, logging.config, json, codecs, time, datetime, urllib
from collections import OrderedDict

from pyutils import Options, LogAdapter, strflocal, localfstr, get_logger, log_level
from pimatic import PimaticAPI


def main():

    from ConfigParser import ConfigParser
    from argparse import ArgumentParser
    from pimatic import __version__, __author__

    node = {'url': None, 'username': None, 'password': None}

    options = {
        'config': '~/.pimatic/pimatic.cfg,~/.pimatic/alarm.cfg',
        'profile': 'default',
        'loglevel_requests': 'ERROR',
        'loglevel': 'DEBUG'
    }

# region Command line arguments

    parser = ArgumentParser(description='pimatic-alarm-config [PimaticAPI Rev. %s (c) %s]' % (__version__, __author__))

    parser.add_argument('-c', '--config', type=str, help='use alternate configuration file(s)')
    parser.add_argument('-s', '--secrets', type=str, help='use alternate secrets file(s)')
    parser.add_argument('-l', '--loglevel', type=str, choices=['DEBUG', 'INFO', 'WARNING', 'ERROR', 'CRITICAL'],
                        help='debug log level')

    parser.add_argument('-n', '--node', type=str, help='pimatic node instance')
    parser.add_argument('-u', '--username', type=str, help='pimatic username')
    parser.add_argument('-p', '--password', type=str, help='pimatic password')

    parser.add_argument('profile', nargs='?', default='default')

    # parser.add_argument('-d', '--device', type=str, help='device specification (regex)')
    # parser.add_argument('-v', '--invert', action='store_true', help='invert regex match')
    # parser.add_argument('-x', '--exclude', type=str, help='device specification (regex)')
    #
    # parser.add_argument('-f', '--format', type=str, choices=['JSON', 'LIST'], help='output format')
    # parser.add_argument('-o', '--order', type=str, help='order by attribute')
    # parser.add_argument('-r', '--reverse', action='store_true', help='reverse sort order')

    args = parser.parse_args()
    opts = Options(options, args, '[config]', prefix='PIMATIC')
    config = opts.config_parser

    if config is None:
        LogAdapter(get_logger(), {'package': 'pimatic-alarm-config'}).critical("Missing configuration file!")
        exit(1)

    logger = LogAdapter(opts.logger, {'package': 'pimatic-alarm-config'})

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

    contacts = None
    section = None


    if config.has_section('profile_' + args.profile):
        section = 'profile_' + args.profile
        contacts = dict(config._sections[section])
    else:
        logger.critical(u'Profile [{}] not found!'.format(args.profile))
        exit(1)

    logger.info(u'Profile [{}] requested'.format(args.profile))

    logger.debug(u'url: %s' % (node['url']))

    with PimaticAPI(server=node['url'],
                    username=node['username'],
                    password=node['password'],
                    logger=logger) as pimatic:

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

        if pimatic.variable('alarmLocked', 1) is None:
            logger.critical(u'Error patching [alarmLocked]')
            exit(5)

        if pimatic.variable('alarmLockedDevice', u'') is None:
            logger.critical(u'Error patching [$alarmLockedDevice]')
            exit(5)

        # create temporary rule
        rule_button = rule_when.split()[1]
        rule_undefined = u'when {} is pressed and if [$alarmProfile = "undefined"] then set $alarmLocked = 1'.format(rule_button)
        result = pimatic.patch('/api/rules/{}'.format(opts.check), {"rule": {"ruleString": rule_undefined}})
        if not result:
            logger.critical(u'Error patching [{}]'.format(opts.check))
            exit(7)

        for contact in contacts:

            # skip meta data from ordered dict representation of config section
            if contact == '__len__' or contact == '__name__': continue

            state = config.getboolean(section, contact)

            logger.info(u'{}: {}'.format(contact, state))

            # device name magic ...
            device = contact.replace('contact_', '')
            device = device.replace('_','-')
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

        rule_condition = rule_condition[:-5]
        rule_string = u'{}[{}]{}'.format(rule_when, rule_condition, rule_then)

        # logger.debug(u'{}: {}'.format(opts.check, rule_string))

        result = pimatic.patch('/api/rules/{}'.format(opts.check), {"rule": {"ruleString": rule_string}})
        if not result:
            logger.error(u'Error patching [{}]'.format(opts.check))

        # TODO: profile => args.profile, locked => 0
        pimatic.variable('alarmProfile', args.profile)

        logger.info(u'Profile [{}] activated'.format(args.profile))


# region __Main__

if __name__ == '__main__':

    main()
    exit(0)

# endregion
