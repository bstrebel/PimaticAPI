#!/usr/bin/env python
# -*- coding: utf-8 -*-

from __future__ import absolute_import
from __future__ import print_function

import os, sys, re, uuid, logging, logging.config, json, codecs, time, datetime, urllib

from pyutils import Options, LogAdapter, strflocal, localfstr, get_logger, log_level, utf8, string
from pimatic.app import PimaticApp

class PimaticEventsApp(PimaticApp):

    options = {
        'app': 'PimaticEventsApp',
        'rev': '0.9.5',
        'config': '~/.pimatic/pimatic.cfg,~/.pimatic/events.cfg',
        'window': '90s',
        'device': '.*',
        'exclude': '(var_|weather|sunrise|forecast|bmp|syssensor)',
        'format': '%Y-%d-%m %H:%M:%S',
        'loglevel_requests': 'ERROR',
        'loglevel': 'DEBUG'
    }

    def __init__(self):

        super(PimaticEventsApp, self).__init__(self.options)

        self._parser.add_argument('-d', '--device', type=str, help='device specification (regex)')
        self._parser.add_argument('-v', '--invert', action='store_true', help='invert regex match')
        self._parser.add_argument('-x', '--exclude', type=str, help='device specification (regex)')
        
        # event only options
        self._parser.add_argument('-a', '--after', type=str, help='after datetime')
        self._parser.add_argument('-b', '--before', type=str, help='before datetime')
        self._parser.add_argument('-t', '--time', type=str, help='datetime spec ')
        self._parser.add_argument('-w', '--window', type=str, help='time window')
        self._parser.add_argument('-o', '--order', type=str, help='order by attribute (default: time)')
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

            if pimatic.check_result(result, 'events'):

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

                logger.info('events: %d (%d)' % (len(events), len(result['events'])))
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

                    print(string(short))


# region __Main__
def main():
    return PimaticEventsApp().run()

if __name__ == '__main__':
    exit(main())
# endregion
