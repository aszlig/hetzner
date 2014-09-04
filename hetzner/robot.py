import json
import logging

from base64 import b64encode

try:
    from httplib import BadStatusLine, ResponseNotReady
except ImportError:
    from http.client import BadStatusLine, ResponseNotReady

try:
    from urllib import urlencode
except ImportError:
    from urllib.parse import urlencode

from hetzner import WebRobotError, RobotError
from hetzner.server import Server
from hetzner.rdns import ReverseDNSManager
from hetzner.util.http import ValidatedHTTPSConnection

ROBOT_HOST = "robot-ws.your-server.de"
ROBOT_WEBHOST = "robot.your-server.de"

__all__ = ['Robot', 'RobotConnection', 'RobotWebInterface', 'ServerManager']


class RobotWebInterface(object):
    """
    This is for scraping the web interface and can be used to implement
    features that are not yet available in the official API.
    """
    def __init__(self, user=None, passwd=None):
        self.conn = None
        self.session_cookie = None
        self.user = user
        self.passwd = passwd
        self.logged_in = False
        self.logger = logging.getLogger("Robot scraper for {0}".format(user))

    def update_session(self, response):
        """
        Parses the session cookie from the given response instance and updates
        self.session_cookie accordingly if a session cookie was recognized.
        """
        for key, value in response.getheaders():
            if key.lower() != 'set-cookie':
                continue
            if not value.startswith("robot="):
                continue
            self.session_cookie = value.split(';', 1)[0]

    def connect(self, force=False):
        """
        Establish a connection to the robot web interface if we're not yet
        connected. If 'force' is set to True, throw away the old connection and
        establish a new one, regardless of whether we are connected or not.
        """
        if force and self.conn is not None:
            self.conn.close()
            self.conn = None
        if self.conn is None:
            self.conn = ValidatedHTTPSConnection(ROBOT_WEBHOST)

    def login(self, user=None, passwd=None, force=False):
        """
        Log into the robot web interface using self.user and self.passwd. If
        user/passwd is provided as arguments, those are used instead and
        self.user/self.passwd are updated accordingly.
        """
        if self.logged_in and not force:
            return

        self.connect(force=force)

        # Update self.user and self.passwd in case we need to re-establish the
        # connection.
        if user is not None:
            self.user = user
        if passwd is not None:
            self.passwd = passwd

        if self.user is None or self.passwd is None:
            raise WebRobotError("Login credentials for the web user interface "
                                "are missing.")

        if self.user.startswith("#ws+"):
            raise WebRobotError("The user {0} is a dedicated web service user "
                                "and cannot be used for scraping the web user "
                                "interface.")

        # This is primarily for getting a first session cookie.
        response = self.request('/login', xhr=False)
        if response.status != 200:
            raise WebRobotError("Invalid status code {0} while visiting login"
                                " page".format(response.status))

        data = {'user': self.user, 'password': self.passwd}
        self.logger.debug("Logging in to Robot web frontend with user %s.",
                          self.user)
        response = self.request('/login/check', data, xhr=False, log=False)

        if response.status != 302 or response.getheader('Location') is None:
            raise WebRobotError("Login to robot web interface failed.")

        self.logged_in = True

    def request(self, path, data=None, xhr=True, method=None, log=True):
        """
        Send a request to the web interface, using 'data' for urlencoded POST
        data. If 'data' is None (which it is by default), a GET request is sent
        instead. A httplib.HTTPResponse is returned on success.

        By default this method uses headers for XMLHttpRequests, so if the
        request should be an ordinary HTTP request, set 'xhr' to False.

        If 'log' is set to False, don't log anything containing data. This is
        useful to prevent logging sensible information such as passwords.
        """
        self.connect()

        headers = {'Connection': 'keep-alive'}
        if self.session_cookie is not None:
            headers['Cookie'] = self.session_cookie
        if xhr:
            headers['X-Requested-With'] = 'XMLHttpRequest'

        if data is None:
            if method is None:
                method = 'GET'
            encoded = None
        else:
            if method is None:
                method = 'POST'
            encoded = urlencode(data)
            headers['Content-Type'] = 'application/x-www-form-urlencoded'

        if log:
            self.logger.debug("Sending %s request to Robot web frontend "
                              "at %s with data %r.",
                              ("XHR " if xhr else "") + method, path, encoded)
        self.conn.request(method, path, encoded, headers)

        try:
            response = self.conn.getresponse()
        except ResponseNotReady:
            self.logger.debug("Connection closed by Robot web frontend,"
                              " retrying.")
            # Connection closed, so we need to reconnect.
            # FIXME: Try to avoid endless loops here!
            self.connect(force=True)
            return self.request(path, data=data, xhr=xhr, log=log)

        if log:
            self.logger.debug("Got response from web frontend with status %d.",
                              response.status)

        self.update_session(response)
        return response


class RobotConnection(object):
    def __init__(self, user, passwd):
        self.user = user
        self.passwd = passwd
        self.conn = ValidatedHTTPSConnection(ROBOT_HOST)
        self.logger = logging.getLogger("Robot of {0}".format(user))

        # Provide this as a way to easily add unsupported API features.
        self.scraper = RobotWebInterface(user, passwd)

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

    def request(self, method, path, data=None, allow_empty=False):
        if data is not None:
            data = urlencode(data)

        auth = 'Basic {0}'.format(b64encode(
            "{0}:{1}".format(self.user, self.passwd).encode('ascii')
        ).decode('ascii'))

        headers = {'Authorization': auth}

        if data is not None:
            headers['Content-Type'] = 'application/x-www-form-urlencoded'

        self.logger.debug("Sending %s request to Robot at %s with data %r.",
                          method, path, data)
        response = self._request(method, path, data, headers)
        raw_data = response.read().decode('utf-8')
        if len(raw_data) == 0 and not allow_empty:
            msg = "Empty response, status {0}."
            raise RobotError(msg.format(response.status), response.status)
        elif not allow_empty:
            try:
                data = json.loads(raw_data)
            except ValueError:
                msg = "Response is not JSON (status {0}): {1}"
                raise RobotError(msg.format(response.status, repr(raw_data)))
        else:
            data = None
        self.logger.debug(
            "Got response from Robot with status %d and data %r.",
            response.status, data
        )

        if 200 <= response.status < 300:
            return data
        else:
            error = data.get('error', None)
            if error is None:
                raise RobotError("Unknown error: {0}".format(data),
                                 response.status)
            else:
                err = "{0} - {1}".format(error['status'], error['message'])
                missing = error.get('missing', [])
                invalid = error.get('invalid', [])
                fields = []
                if missing is not None:
                    fields += missing
                if invalid is not None:
                    fields += invalid
                if len(fields) > 0:
                    err += ", fields: {0}".format(', '.join(fields))
                raise RobotError(err, response.status)

    get = lambda s, p: s.request('GET', p)
    post = lambda s, p, d: s.request('POST', p, d)
    put = lambda s, p, d: s.request('PUT', p, d)
    delete = lambda s, p, d=None: s.request('DELETE', p, d, allow_empty=True)


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
        self.rdns = ReverseDNSManager(self.conn)
