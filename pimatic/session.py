#!/usr/bin/env python
# -*- coding: utf-8 -*-

import sys, os, time, requests, json, re, logging
from pyutils import LogAdapter, get_logger

class PimaticAPI(object):

    _session = None

    @staticmethod
    def hide_password(msg):
        if msg:
            msg = re.sub('"password": ".*"', '"password": "*****"', msg, re.IGNORECASE)
        return msg

    @staticmethod
    def check_result(result, key):
        if result is not None and result.get(key) is not None:
            return True
        return False

    @staticmethod
    def eventparms(criteria):
        parms = {}
        for k in criteria:
            if criteria[k] is not None:
                parms['criteria[' + k + ']'] = criteria[k]
        return parms

    def __init__(self, server="http://localhost:8080", username="admin", password="admin", logger=None):

        self._server = server
        self._username = username
        self._password = password
        self._session = None
        self._cookies = None
        self._offline = None
        self._response = None
        self._content = None

        self._devices = None
        self._rules = None

        if logger is None:
            self._logger = get_logger('pimatic', logging.DEBUG)
        else:
            self._logger = logger

        self._adapter = LogAdapter(self._logger, {'package': 'pimatic', 'callback': PimaticAPI.hide_password})

    def __enter__(self):
        self.login()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        if self:
            if self.authenticated:
                self.logout()

    @property
    def logger(self):
        return self._adapter

    @property
    def authenticated(self): return self._cookies is not None

    @property
    def success(self): return ( self._response and self._response.get('success') == True )

    @property
    def response(self): return self._response

    @property
    def content(self): return self._content

    @property
    def devices(self):
        if self._devices is None:
            if not self.authenticated:
                self.login()
            result = self.get('/api/devices')
            if self.check_result(result,'devices'):
                self._devices = {}
                for device in result['devices']:
                    self._devices[device['id']] = device
        return self._devices

    @property
    def rules(self):
        if self._rules is None:
            if not self.authenticated:
                self.login()
            result = self.get('/api/rules')
            if self.check_result(result,'rules'):
                self._rules = {}
                for rule in result['rules']:
                    self._rules[rule['id']] = rule
        return self._rules


    def _check_response(self, response):
        """
        Post process web request response
        :param response: web request response
        :return: json object content
        """
        content = None
        self._content = None
        if response:
            if response.status_code == 200:
                # pimatic session cookies
                if self._cookies is None:
                    self._cookies = response.cookies;
                if response.content:
                    self.logger.debug("Response content: [%s]" % (response.content.decode('utf-8')))
                    if response.content.startswith('{'):
                        content = response.json(encoding='UTF-8')
                        if not content.get('success'):
                            # print(json.dumps(content, indent=4, ensure_ascii=False, encoding='utf-8'))
                            self.logger.error(json.dumps(content, ensure_ascii=False, encoding='utf-8'))
                        self._content = content
                        return content
                self._content = response.content
                return response.content
            else:
                self.logger.error("Response: %d" % (response.status_code))
                # print(response.status_code)
        return None

    def _url(self, path):
        """
        Pre process web request
        :param path:
        :return: formatted URL
        """
        if not path.startswith('/'):
            path = '/' + path
        url = self._server + path
        self.logger.debug("Request url: %s" % (url))
        return url

    def _request(self, call, path, data=None, headers=None):
        response = None
        self._response = None
        self._content = None
        try:
            self._offline = True
            self.logger.debug('Request call: [%s] with body %s' % (call.func_name, data))
            response = call(self._url(path), cookies=self._cookies, data=data, headers=headers)
            self.logger.debug('Request url: %s' % (response.request.path_url))
        except requests.exceptions.RequestException as e:
            self.logger.error("Request exception: %s" % (e))
            return None
        self._offline = False
        self._response = response
        return self._check_response(response)

    def get(self, path):
        return self._request(requests.get, path)

    def delete(self, path):
        return self._request(requests.delete, path)

    def post(self, path, data=None):
        if data:
            body = json.dumps(data)
        return self._request(requests.post, path, data=body, headers={'Content-Type': 'application/json'})

    def put(self, path, data=None):
        body = None
        if data:
            # if isinstance(data, dict):
            #     body = json.dumps(data,ensure_ascii=False,encoding='utf-8')
            # body = json.dumps(data,ensure_ascii=False,encoding='utf-8')
            body = json.dumps(data)
        return self._request(requests.put, path, data=body, headers={'Content-Type': 'application/json'})

    def patch(self, path, data=None):
        body = None
        if data:
            # if isinstance(data, dict):
            #     body = json.dumps(data,ensure_ascii=False,encoding='utf-8')
            # body = json.dumps(data,ensure_ascii=False,encoding='utf-8')
            body = json.dumps(data)
        return self._request(requests.patch, path, data=body, headers={'Content-Type': 'application/json'})

    def login(self, username=None, password=None):
        if username: self._username = username
        if password: self._password = password
        data = {"username": self._username, "password": self._password}
        content = self.post('login', data)
        # content =  self._request(requests.post, 'login', data)
        if content and self._cookies:
            self._session = self._cookies['pimatic.sess']
            self.logger.debug("User %s successfully logged in at %s" % (self._username, self._server))
        else:
            self.logger.error("Login for %s at %s failed" % (self._username, self._server))

    def logout(self):
        self._session = None
        self._cookies = None
        self.logger.debug("User %s logged out!" % (self._username))


# region __main__

if __name__ == '__main__':

    # server = None
    # user = None
    # password = None
    #
    # if len(sys.argv) > 3:
    #     server = sys.argv[1]
    #     user = sys.argv[2]
    #     password = sys.argv[3]
    # else:
    #     server = os.environ.get('OX_SERVER')
    #     user = os.environ.get('OX_USER')
    #     password = os.environ.get('OX_PASSWORD')

    with PimaticAPI() as pimatic:
        pimatic.login('admin', 'admin')
        # print(pimatic.authenticated)
        pimatic.patch('/api/rules/dummy', {"rule":{"active":False}})
        pimatic.get('/api/device/switch_alarm_system/turnOn')
        pimatic.post('/api/rules/new_rule',
                     {"rule": {"name": "new rule", "ruleString": "if pimatic is starting then log \"DUMMY\"", "active": True, "logging": True}})

    with PimaticAPI() as pimatic:
        pimatic.login('admin', 'admin')
        # print(pimatic.authenticated)
        pimatic.patch('/api/rules/dummy', {"rule":{"active":False}})
        pimatic.get('/api/device/switch_alarm_system/turnOn')
        pimatic.post('/api/rules/new_rule',
                     {"rule": {"name": "new rule", "ruleString": "if pimatic is starting then log \"DUMMY\"", "active": True, "logging": True}})


# endregion


