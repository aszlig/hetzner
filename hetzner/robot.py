import re
import json
import hashlib

from base64 import b64encode
from urllib import urlencode
from httplib import HTTPSConnection, BadStatusLine, ResponseNotReady

from hetzner.server import Server

ROBOT_HOST = "robot-ws.your-server.de"
ROBOT_WEBHOST = "robot.your-server.de"


class RobotError(Exception):
    pass


class ManualReboot(Exception):
    pass


class ConnectError(Exception):
    pass


class WebRobotError(RobotError):
    pass


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
            self.conn = HTTPSConnection(ROBOT_WEBHOST)

    def login(self, user=None, passwd=None):
        """
        Log into the robot web interface using self.user and self.passwd. If
        user/passwd is provided as arguments, those are used instead and
        self.user/self.passwd are updated accordingly.
        """
        if self.logged_in:
            return

        self.connect()

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
        response = self.request('/login/check', data, xhr=False)

        if response.status != 302 or response.getheader('Location') is None:
            raise WebRobotError("Login to robot web interface failed.")

        self.logged_in = True

    def get_serverid(self, ip):
        """
        Retrieve and return server ID for the main IP address supplied by 'ip'.
        """
        self.login()
        serverid_re = re.compile(r'value="(\d+)"[^#]*#\1 \((.*?)\)')
        data = self.request('/support/server', {}).read()
        idstr = dict(map(reversed, serverid_re.findall(data))).get(str(ip))
        if idstr is None:
            raise WebRobotError("Server ID for IP address {0} not"
                                " found.".format(ip))
        return int(idstr)

    def request(self, path, data=None, xhr=True):
        """
        Send a request to the web interface, using 'data' for urlencoded POST
        data. If 'data' is None (which it is by default), a GET request is sent
        instead. A httplib.HTTPResponse is returned on success.

        By default this method uses headers for XMLHttpRequests, so if the
        request should be an ordinary HTTP request, set 'xhr' to False.
        """
        self.connect()

        headers = {'Connection': 'keep-alive'}
        if self.session_cookie is not None:
            headers['Cookie'] = self.session_cookie
        if xhr:
            headers['X-Requested-With'] = 'XMLHttpRequest'

        if data is None:
            method = 'GET'
            encoded = None
        else:
            method = 'POST'
            encoded = urlencode(data)
            headers['Content-Type'] = 'application/x-www-form-urlencoded'

        self.conn.request(method, path, encoded, headers)

        # Minimal peer certificate validation using a fingerprint
        cert = self.conn.sock.getpeercert(binary_form=True)
        fpr = hashlib.sha256(cert).hexdigest()
        # XXX: Using static fingerprint here until we have implemented #2.
        assert fpr == ('c34204f4ffd7df006311a9275fc62e42'
                       '8a1ccdd71514bfd4aafb7a5b435cbc17')

        try:
            response = self.conn.getresponse()
        except ResponseNotReady:
            # Connection closed, so we need to reconnect.
            # FIXME: Try to avoid endless loops here!
            self.connect(force=True)
            return self.request(path, data=data, xhr=xhr)

        self.update_session(response)
        return response


class RobotConnection(object):
    def __init__(self, user, passwd):
        self.user = user
        self.passwd = passwd
        self.conn = HTTPSConnection(ROBOT_HOST)

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
        raw_data = response.read()
        if len(raw_data) == 0:
            msg = "Empty resonse, status {0}."
            raise RobotError(msg.format(response.status))
        try:
            data = json.loads(raw_data)
        except ValueError:
            msg = "Response is not JSON (status {0}): {1}"
            raise RobotError(msg.format(response.status, repr(raw_data)))

        if 200 <= response.status < 300:
            return data
        else:
            error = data.get('error', None)
            if error is None:
                raise RobotError("Unknown error: {0}".format(data))
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
