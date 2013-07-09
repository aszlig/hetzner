import json

from base64 import b64encode
from urllib import urlencode
from httplib import HTTPSConnection, BadStatusLine

from hetzner.server import Server

ROBOT_HOST = "robot-ws.your-server.de"


class RobotError(Exception):
    pass


class ManualReboot(Exception):
    pass


class ConnectError(Exception):
    pass


class RobotConnection(object):
    def __init__(self, user, passwd):
        self.user = user
        self.passwd = passwd
        self.conn = HTTPSConnection(ROBOT_HOST)

    def _request(self, method, path, data, headers, retry=1):
        self.conn.request(method.upper(), path, data, headers)
        try:
            return self.conn.getresponse()
        except BadStatusLine:
            # XXX: Sometimes, the API server seems to have a problem with
            # keepalives.
            if retry <= 0:
                raise

            self.conn.close()
            self.conn.connect()
            return self._request(method, path, data, headers, retry - 1)

    def request(self, method, path, data=None):
        if data is not None:
            data = urlencode(data)

        auth = 'Basic {0}'.format(
            b64encode("{0}:{1}".format(self.user, self.passwd))
        )

        headers = {'Authorization': auth}

        if data is not None:
            headers['Content-Type'] = 'application/x-www-form-urlencoded'

        response = self._request(method, path, data, headers)
        data = json.loads(response.read())

        if 200 <= response.status < 300:
            return data
        else:
            error = data.get('error', None)
            if error is None:
                raise RobotError("Unknown error: {0}".format(data))
            else:
                err = "{0} - {1}".format(error['status'], error['message'])
                if 'missing' in error:
                    err += ", missing input: {0}".format(
                        ', '.join(error['missing'])
                    )
                if 'invalid' in error:
                    err += ", invalid input: {0}".format(
                        ', '.join(error['invalid'])
                    )
                raise RobotError(err)

    get = lambda s, p: s.request('GET', p)
    post = lambda s, p, d: s.request('POST', p, d)
    put = lambda s, p, d: s.request('PUT', p, d)
    delete = lambda s, p, d: s.request('DELETE', p, d)


class ServerManager(object):
    def __init__(self, conn):
        self.conn = conn

    def get(self, ip):
        """
        Get server by providing its main IP address.
        """
        return Server(self.conn, self.conn.get('/server/{0}'.format(ip)))

    def __iter__(self):
        return iter([Server(self.conn, s) for s in self.conn.get('/server')])


class Robot(object):
    def __init__(self, user, passwd):
        self.conn = RobotConnection(user, passwd)
        self.servers = ServerManager(self.conn)
