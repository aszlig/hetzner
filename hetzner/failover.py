from hetzner import RobotError

__all__ = ['Failover', 'FailoverManager']


class Failover(object):
    ip = None
    server_ip = None
    server_number = None
    active_server_ip = None

    def __repr__(self):
        return "%s (destination: %s, booked on %s (%s))" % (
            self.ip, self.active_server_ip, self.server_number, self.server_ip)

    def __init__(self, data):
        for attr, value in data.items():
            if hasattr(self, attr):
                setattr(self, attr, value)


class FailoverManager(object):
    def __init__(self, conn, servers):
        self.conn = conn
        self.servers = servers

    def list(self):
        failovers = {}
        try:
            ips = self.conn.get('/failover')
        except RobotError as err:
            if err.status == 404:
                return failovers
            else:
                raise
        for ip in ips:
            failover = Failover(ip.get('failover'))
            failovers[failover.ip] = failover
        return failovers

    def set(self, ip, new_destination):
        failovers = self.list()
        if ip not in failovers.keys():
            raise RobotError(
                "Invalid IP address '%s'. Failover IP addresses are %s"
                % (ip, failovers.keys()))
        failover = failovers.get(ip)
        if new_destination == failover.active_server_ip:
            raise RobotError(
                "%s is already the active destination of failover IP %s"
                % (new_destination, ip))
        available_dests = [s.ip for s in list(self.servers)]
        if new_destination not in available_dests:
            raise RobotError(
                "Invalid destination '%s'. "
                "The destination is not in your server list: %s"
                % (new_destination, available_dests))
        result = self.conn.post('/failover/%s'
                                % ip, {'active_server_ip': new_destination})
        return Failover(result.get('failover'))
