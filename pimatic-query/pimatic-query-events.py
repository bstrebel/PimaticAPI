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
        'config': '~/.pimatic/pimatic.cfg,~/.pimatic/events.cfg',
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

    # event only options
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

# region Process device list
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
        devices = []
        for id in pimatic.devices:
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
        logger.info(u'devices: %d (%d)' % (len(devices), len(pimatic.devices)))
        # for id in devices: print(id)
# endregion

        criteria = {'deviceId': None, 'order': 'time', 'attributeName': None, 'after': None, 'before': None,
                    'orderDirection': None, 'offset': None, 'limit': None}

# region Process time frame settings
        if opts.time:
            time = opts.time
            delta = opts.window
            tokens = opts.time.split()
            if re.match('[0-9,.]+[smhd]', tokens[-1]):
                delta = tokens[-1]
                time = " ".join(tokens[0:-1])
            logger.info('time: %s' % (time))
            logger.info('delta: %s' % (delta))
            criteria['after'] = localfstr('{} -{}'.format(time, delta)) * 1000
            criteria['before'] = localfstr('{} +{}'.format(time, delta)) * 1000
        else:
            if opts.after:
                logger.info('after: %s' % (opts.after))
                criteria['after'] = localfstr(opts.after) * 1000
            if opts.before:
                logger.info('before: %s' % (opts.before))
                criteria['before'] = localfstr(opts.before) * 1000

        if criteria['after']:
            logger.info('after: %s' % strflocal(criteria['after']))
        if criteria['before']:
            logger.info('before: %s' % strflocal(criteria['before']))
# endregion

        if len(devices) == 1:
            criteria['deviceId'] = devices[0]

        logger.debug(u'criteria %s' % criteria)

        result = pimatic.get('/api/database/device-attributes/?' +
                             urllib.urlencode(pimatic.eventparms(criteria)))

        if pimatic.check_result(result,'events'):

            events = []
            width = {'deviceId': 0, 'attributeName': 0, 'type': 0, 'cname': 0, 'label': 0}

            def events_append(event):

                if pimatic.devices.get(event['deviceId']):

                    device = pimatic.devices[event['deviceId']]
                    event['cname'] = device['config']['class']
                    for attribute in device['attributes']:
                        if attribute['name'] == event['attributeName']: break
                    event['label'] = attribute['label']
                    if attribute['type'] == 'boolean':
                        event['value'] = attribute['labels'][int(not event['value'])]

                    if not opts.get('pir_absent', True):
                        if event['cname'] == u'HomeduinoRFPir' and event['value'] == u'absent':
                            return

                for k in width:
                    width[k] = max(width[k], len(event[k]))

                events.append(event)

            for event in result['events']:
                # this should not be should not be necessary :-(
                if criteria['after'] and event['time'] <= criteria['after']: continue
                if criteria['before'] and event['time'] >= criteria['before']: continue
                id = event['deviceId']
                if exclude is not None:
                    if not exclude.search(id):
                        if pattern is not None:
                            if inverse:
                                if not pattern.search(id): events_append(event)
                            else:
                                if pattern.search(id): events_append(event)
                        else:
                            events_append(event)

            logger.info('events: %d (%d)' % (len(events),len(result['events'])))
            for event in events:

                # long = u'{} {:{device}} {:{cname}} {:{attribute}} {:{label}} {:{type}} {}'.format(
                #     strflocal(event['time']),
                #     event['deviceId'],
                #     event['cname'],
                #     event['attributeName'],
                #     event['label'],
                #     event['type'],
                #     event['value'],
                #     device=width['deviceId'],cname=width['cname'], attribute=width['attributeName'], label=width['label'], type=width['type']
                # )

                short = u'{} {:{device}} {:{attribute}} {}'.format(
                    strflocal(event['time']),
                    event['deviceId'],
                    event['attributeName'],
                    event['value'],
                    device=width['deviceId'], attribute=width['attributeName']
                )

                print(short)


# region __Main__

if __name__ == '__main__':

    main()
    exit(0)

# endregion
