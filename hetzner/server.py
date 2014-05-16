import os
import re
import sys
import time
import random
import socket
import string
import subprocess

from tempfile import mkdtemp
from datetime import datetime
from urllib import urlencode

from hetzner import util, RobotError, ManualReboot, ConnectError
from hetzner.rdns import ReverseDNS, ReverseDNSManager


class SSHAskPassHelper(object):
    """
    This creates a temporary SSH askpass helper script, which just passes the
    provided password.
    """
    def __init__(self, passwd):
        self.passwd = passwd
        self.tempdir = None
        self.script = None

    def __enter__(self):
        self.tempdir = mkdtemp()
        script = os.path.join(self.tempdir, "askpass")
        fd = os.open(script, os.O_WRONLY | os.O_CREAT | os.O_NOFOLLOW, 0700)
        self.script = script
        esc_passwd = self.passwd.replace("'", r"'\''")
        os.write(fd, "#!/bin/sh\necho -n '{0}'".format(esc_passwd))
        os.close(fd)
        return script

    def __exit__(self, type, value, traceback):
        if self.script is not None:
            os.unlink(self.script)
        if self.tempdir is not None:
            os.rmdir(self.tempdir)


class RescueSystem(object):
    def __init__(self, server):
        self.server = server
        self.conn = server.conn

        self._active = None
        self._password = None

    def _fetch_status(self):
        reply = self.conn.get('/boot/{0}/rescue'.format(self.server.ip))
        data = reply['rescue']
        self._active = data['active']
        self._password = data['password']

    @property
    def active(self):
        if self._active is not None:
            return self._active
        self._fetch_status()
        return self._active

    @property
    def password(self):
        if self._password is not None:
            return self._password
        self._fetch_status()
        return self._password

    def _rescue_action(self, method, opts=None):
        reply = self.conn.request(
            method,
            '/boot/{0}/rescue'.format(self.server.ip),
            opts
        )

        data = reply['rescue']
        self._active = data['active']
        self._password = data['password']

    def activate(self, bits=64, os='linux'):
        """
        Activate the rescue system if necessary.
        """
        if not self.active:
            opts = {'os': os, 'arch': bits}
            return self._rescue_action('post', opts)

    def deactivate(self):
        """
        Deactivate the rescue system if necessary.
        """
        if self.active:
            return self._rescue_action('delete')

    def observed_activate(self, *args, **kwargs):
        """
        Activate the rescue system and reboot into it.
        Look at Server.observed_reboot() for options.
        """
        self.activate()
        self.server.observed_reboot(*args, **kwargs)

    def observed_deactivate(self, *args, **kwargs):
        """
        Deactivate the rescue system and reboot into normal system.
        Look at Server.observed_reboot() for options.
        """
        self.deactivate()
        self.server.observed_reboot(*args, **kwargs)

    def shell(self, *args, **kwargs):
        """
        Reboot into rescue system, spawn a shell and after the shell is
        closed, reboot back into the normal system.

        Look at Server.observed_reboot() for further options.
        """
        self.observed_activate(*args, **kwargs)

        with SSHAskPassHelper(self.password) as askpass:
            self.server.shell(args, kwargs, askpass=askpass)

        self.observed_deactivate(*args, **kwargs)


class AdminAccount(object):
    def __init__(self, server):
        # XXX: This is preliminary, because we don't have such functionality in
        #      the official API yet.
        self._scraper = server.conn.scraper
        self._serverid = server.number
        self.exists = False
        self.login = None
        self.passwd = None
        self.update_info()

    def update_info(self):
        """
        Get information about currently active admin login.
        """
        self._scraper.login()
        login_re = re.compile(r'"label_req">Login.*?"element">([^<]+)',
                              re.DOTALL)

        path = '/server/admin/id/{0}'.format(self._serverid)
        response = self._scraper.request(path)
        assert response.status == 200
        match = login_re.search(response.read())
        if match is None:
            self.exists = False
        else:
            self.exists = True
            self.login = match.group(1)

    def _genpasswd(self):
        random.seed(os.urandom(512))
        chars = string.letters + string.digits + "/()-=+_,;.^~#*@"
        length = random.randint(20, 40)
        return ''.join(random.choice(chars) for i in range(length))

    def create(self, passwd=None):
        """
        Create a new admin account if missing. If passwd is supplied, use it
        instead of generating a random one.
        """
        if not self.exists:
            path = '/server/adminCreate/id/{0}'.format(self._serverid)
            self._scraper.request(path)
            self.update_info()
        if passwd is None:
            passwd = self._genpasswd()
        data = {
            'password[new_password]': passwd,
            'password[new_password_repeat]': passwd,
            'id': self._serverid
        }
        response = self._scraper.request('/server/adminUpdate', data)
        assert "msgbox_success" in response.read()
        self.passwd = passwd
        return self.login, self.passwd

    def delete(self):
        """
        Remove the admin account.
        """
        if not self.exists:
            return
        path = '/server/adminDelete/id/{0}'.format(self._serverid)
        assert "msgbox_success" in self._scraper.request(path).read()
        self.update_info()

    def __repr__(self):
        if self.exists:
            return "<AdminAccount login: {0}>".format(self.login)
        else:
            return "<AdminAccount missing>"


class IpAddress(object):
    def __init__(self, conn, result, subnet_ip=None):
        self.conn = conn
        self.subnet_ip = subnet_ip
        self.update_info(result)
        self._rdns = None

    @property
    def rdns(self):
        """
        Get or set reverse DNS PTRs.
        """
        if self._rdns is None:
            self._rdns = ReverseDNS(self.conn, self.ip)
        return self._rdns

    def update_info(self, result=None):
        """
        Update the information of the current IP address and all related
        information such as traffic warnings. If result is omitted, a new
        request is sent to the robot to gather the information.
        """
        if self.subnet_ip is not None:
            if result is None:
                result = self.conn.get('/subnet/{0}'.format(self._subnet_addr))
            data = result['subnet']
            self._subnet_addr = data['ip']
            data['ip'] = self.subnet_ip
            # Does not exist in subnets
            data['separate_mac'] = None
        else:
            if result is None:
                result = self.conn.get('/ip/{0}'.format(self.ip))
            data = result['ip']

        self.ip = data['ip']
        self.server_ip = data['server_ip']
        self.locked = data['locked']
        self.separate_mac = data['separate_mac']
        self.traffic_warnings = data['traffic_warnings']
        self.traffic_hourly = data['traffic_hourly']
        self.traffic_daily = data['traffic_daily']
        self.traffic_monthly = data['traffic_monthly']

    def __repr__(self):
        return "<IpAddress {0}>".format(self.ip)


class IpManager(object):
    def __init__(self, conn, main_ip):
        self.conn = conn
        self.main_ip = main_ip

    def get(self, ip):
        """
        Get a specific IP address of a server.
        """
        return IpAddress(self.conn, self.conn.get('/ip/{0}'.format(ip)))

    def __iter__(self):
        data = urlencode({'server_ip': self.main_ip})
        result = self.conn.get('/ip?{0}'.format(data))
        return iter([IpAddress(self.conn, ip) for ip in result])


class Subnet(object):
    def __init__(self, conn, result):
        self.conn = conn
        self.update_info(result)

    def update_info(self, result=None):
        """
        Update the information of the subnet. If result is omitted, a new
        request is sent to the robot to gather the information.
        """
        if result is None:
            result = self.conn.get('/subnet/{0}'.format(self.net_ip))

        data = result['subnet']

        self.net_ip = data['ip']
        self.mask = data['mask']
        self.gateway = data['gateway']
        self.server_ip = data['server_ip']
        self.failover = data['failover']
        self.locked = data['locked']
        self.traffic_warnings = data['traffic_warnings']
        self.traffic_hourly = data['traffic_hourly']
        self.traffic_daily = data['traffic_daily']
        self.traffic_monthly = data['traffic_monthly']

        self.is_ipv6, self.numeric_net_ip = util.parse_ipaddr(self.net_ip)
        self.numeric_gateway = util.parse_ipaddr(self.gateway, self.is_ipv6)
        getrange = util.get_ipv6_range if self.is_ipv6 else util.get_ipv4_range
        self.numeric_range = getrange(self.numeric_net_ip, self.mask)

    def get_ip_range(self):
        """
        Return the smallest and biggest possible IP address of the current
        subnet.
        """
        convert = util.ipv6_bin2addr if self.is_ipv6 else util.ipv4_bin2addr
        return convert(self.numeric_range[0]), convert(self.numeric_range[1])

    def __contains__(self, addr):
        """
        Check whether a specific IP address is within the current subnet.
        """
        numeric_addr = util.parse_ipaddr(addr, self.is_ipv6)
        return self.numeric_range[0] <= numeric_addr <= self.numeric_range[1]

    def get_ip(self, addr):
        """
        Return an IpAddress object for the specified IPv4 or IPv6 address or
        None if the IP address doesn't exist in the current subnet.
        """
        if addr in self:
            result = self.conn.get('/subnet/{0}'.format(self.net_ip))
            return IpAddress(self.conn, result, addr)
        else:
            return None

    def __repr__(self):
        return "<Subnet {0}/{1} (Gateway: {2})>".format(self.net_ip, self.mask,
                                                        self.gateway)


class SubnetManager(object):
    def __init__(self, conn, main_ip):
        self.conn = conn
        self.main_ip = main_ip

    def get(self, net_ip):
        """
        Get a specific subnet of a server.
        """
        return Subnet(self.conn, self.conn.get('/subnet/{0}'.format(net_ip)))

    def __iter__(self):
        data = urlencode({'server_ip': self.main_ip})
        try:
            result = self.conn.get('/subnet?{0}'.format(data))
        except RobotError as err:
            # If there are no subnets a 404 is returned rather than just an
            # empty list.
            if err.status == 404:
                result = []
        return iter([Subnet(self.conn, net) for net in result])


class Server(object):
    def __init__(self, conn, result):
        self.conn = conn
        self.update_info(result)
        self.rescue = RescueSystem(self)
        self.ips = IpManager(self.conn, self.ip)
        self.subnets = SubnetManager(self.conn, self.ip)
        self.rdns = ReverseDNSManager(self.conn, self.ip)
        self._admin_account = None

    @property
    def admin(self):
        """
        Update, create and delete admin accounts.
        """
        if self._admin_account is None:
            self._admin_account = AdminAccount(self)
        return self._admin_account

    def update_info(self, result=None):
        """
        Updates the information of the current Server instance either by
        sending a new GET request or by parsing the response given by result.
        """
        if result is None:
            result = self.conn.get('/server/{0}'.format(self.ip))

        data = result['server']

        self.ip = data['server_ip']
        self.number = data['server_number']
        self.name = data['server_name']
        self.product = data['product']
        self.datacenter = data['dc']
        self.traffic = data['traffic']
        self.flatrate = data['flatrate']
        self.status = data['status']
        self.throttled = data['throttled']
        self.cancelled = data['cancelled']
        self.paid_until = datetime.strptime(data['paid_until'], '%Y-%m-%d')
        self.is_vserver = self.product.startswith('VQ')
        self.is_dell = self.product.startswith('DELL')

    def set_name(self, name):
        result = self.conn.post('/server/{0}'.format(self.ip),
                                {'server_name': name})
        self.update_info(result)

    def check_ssh(self, port=22, timeout=5):
        """
        Check if the current server has an open SSH port. Return True if port
        is reachable, otherwise false. Time out after 'timeout' seconds.
        """
        success = True
        old_timeout = socket.getdefaulttimeout()
        socket.setdefaulttimeout(5)

        try:
            s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            s.connect((self.ip, port))
            s.close()
        except socket.error:
            success = False

        socket.setdefaulttimeout(old_timeout)
        return success

    def observed_reboot(self, patience=300, tries=None, manual=False):
        """
        Reboot and wait patience seconds until the system comes back.
        If not, retry with the next step in tries and wait another patience
        seconds. Repeat until there are no more tries left.

        If manual is true, do a manual reboot in case the server doesn't come
        up again. Raises a ManualReboot exception if that is the case.

        Return True on success and False if the system didn't come up.
        """
        is_down = False

        if tries is None:
            if self.is_dell:
                tries = ['ssh', 'rac']

                # These servers take more than 5 minutes to reboot.
                if patience <= 300:
                    patience = 600
            elif self.is_vserver:
                tries = ['hard']
            else:
                tries = ['soft', 'hard']

        for mode in tries:
            print("Rebooting mode: {0}".format(mode))
            if not self.reboot(mode):
                continue

            sys.stdout.write("Waiting for the server to come back")
            sys.stdout.flush()
            now = time.time()
            while True:
                if time.time() > now + patience:
                    break

                is_up = self.check_ssh()
                time.sleep(1)

                if is_up and is_down:
                    return
                elif not is_down:
                    is_down = not is_up
                sys.stdout.write(".")
                sys.stdout.flush()
        if manual:
            self.reboot('manual')
            raise ManualReboot("Issued a manual reboot because the server"
                               " did not come back to life.")
        else:
            raise ConnectError("Server keeps playing dead after reboot :-(")

    def reboot(self, mode='soft'):
        """
        Reboot the server, modes are "soft" for reboot by triggering Ctrl-Alt-
        Del, "hard" for triggering a hardware reset and "manual" for requesting
        a poor devil from the data center to go to your server and press the
        power button.

        On a vServer, rebooting with mode="soft" is a no-op, any other value
        results in a hard reset.
        """

        if self.is_dell:
            if mode == "ssh":
                # XXX: Warning, this only works for linux/unix systems.

                try:
                    self.shell(None, cmdline="reboot")
                except Exception, ex:
                    print ex
                    return False

                return True
            elif mode == "rac":
                try:
                    ips = list(self.ips)
                    ip = ips[1].ip
                except:
                    ip = ""

                rac = RAC(ip)
                rac.powercycle()

                return True
            if mode != "ssh":
                raise RobotError("DELL servers don't allow reboot via robot.")

        if self.is_vserver:
            if mode == 'soft':
                return

            self.conn.scraper.login(force=True)
            baseurl = '/server/vserverCommand/id/{0}/command/reset'
            url = baseurl.format(self.number)
            response = self.conn.scraper.request(url, method='POST')
            assert "msgbox_success" in response.read()
            return response

        modes = {
            'manual': 'man',
            'hard': 'hw',
            'soft': 'sw',
        }

        modekey = modes.get(mode, modes['soft'])
        return self.conn.post('/reset/{0}'.format(self.ip), {'type': modekey})

    def shell(self, *args, **kwargs):
        env = dict(os.environ)

        if "askpass" in kwargs:
            env['SSH_ASKPASS'] = kwargs.get("askpass")

        ssh_options = [
            'CheckHostIP=no',
            'GlobalKnownHostsFile=/dev/null',
            'UserKnownHostsFile=/dev/null',
            'StrictHostKeyChecking=no',
            'LogLevel=quiet',
        ]
        ssh_args = reduce(lambda acc, opt: acc + ['-o', opt],
                          ssh_options, [])
        cmd = (['ssh'] +
               ssh_args +
               ["root@{0}".format(self.ip)] +
               [kwargs.get("cmdline", "")])

        env['DISPLAY'] = ":666"
        subprocess.check_call(cmd, env=env, preexec_fn=os.setsid)

    def __repr__(self):
        return "<{0} (#{1} {2})>".format(self.ip, self.number, self.product)


# Code got from https://github.com/migrantgeek/python-rac

class RAC(object):

    def __init__(self, host):
        import getpass
        self.sid = None

        self.host = raw_input("IP of the iDRAC console [{0}]:".format(host)) or host
        self.username = raw_input("Username [root]:") or "root"
        self.password = getpass.getpass("Password:")

    def _inject_header(self, data):
        if data is not None:
            return "<?xml version='1.0'?>" + data

    def _extract_value(self, data, value):
        if data is None:
            return
        try:
            return data.split('<%s>' % value)[1].split('</%s>' % value)[0]
        except KeyError:
            raise Exception('unable to extract %s' % value)

    def _extract_sid(self, data):
        return self._extract_value(data, 'SID')

    def _extract_cmd_output(self, data):
        return self._extract_value(data, 'CMDOUTPUT')

    def _make_request(self, uri, data=None):
        import urllib2

        opener = urllib2.build_opener()
        if self.sid:
            opener.addheaders.append(('Cookie', 'sid=%s' % self.sid))
        return opener.open('https://%s/cgi-bin/%s' % (self.host, uri),
                self._inject_header(data)).read()

    def _login(self):
        data = '<LOGIN><REQ><USERNAME>%s</USERNAME><PASSWORD>%s</PASSWORD></REQ></LOGIN>' % (self.username, self.password)
        resp = self._make_request('/login', data)
        self.sid = self._extract_sid(resp)

    def _logout(self):
        self.sid = None
        self._make_request('/logout')

    def run_command(self, cmd):
        if self.sid is None:
            self._login()
        try:
            data = '<EXEC><REQ><CMDINPUT>racadm %s</CMDINPUT><MAXOUTPUTLEN>0x0fff</MAXOUTPUTLEN></REQ></EXEC>' % cmd
            return self._extract_cmd_output(self._make_request('/exec', data)).strip()
        finally:
            self._logout()

    def powercycle(self):
        return self.run_command('serveraction powercycle')
