try:
    from urllib import urlencode
except ImportError:
    from urllib.parse import urlencode

from hetzner import RobotError

__all__ = ['ReverseDNS', 'ReverseDNSManager']


class ReverseDNS(object):
    def __init__(self, conn, ip=None, result=None):
        self.conn = conn
        self.ip = ip
        self.update_info(result)

    def update_info(self, result=None):
        if result is None:
            try:
                result = self.conn.get('/rdns/{0}'.format(self.ip))
            except RobotError as err:
                if err.status == 404:
                    result = None
                else:
                    raise

        if result is not None:
            data = result['rdns']
            self.ip = data['ip']
            self.ptr = data['ptr']
        else:
            self.ptr = None

    def set(self, value):
        self.conn.post('/rdns/{0}'.format(self.ip), {'ptr': value})

    def remove(self):
        self.conn.delete('/rdns/{0}'.format(self.ip))

    def __repr__(self):
        return "<ReverseDNS PTR: {0}>".format(self.ptr)


class ReverseDNSManager(object):
    def __init__(self, conn, main_ip=None):
        self.conn = conn
        self.main_ip = main_ip

    def get(self, ip):
        return ReverseDNS(self.conn, ip)

    def __iter__(self):
        if self.main_ip is None:
            url = '/rdns'
        else:
            data = urlencode({'server_ip': self.main_ip})
            url = '/rdns?{0}'.format(data)
        try:
            result = self.conn.get(url)
        except RobotError as err:
            if err.status == 404:
                result = []
            else:
                raise
        return iter([ReverseDNS(self.conn, result=rdns) for rdns in result])
