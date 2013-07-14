import os
import time
import socket
import subprocess

from tempfile import mkdtemp
from datetime import datetime


class ManualReboot(Exception):
    pass


class ConnectError(Exception):
    pass


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
            ssh_options = [
                'CheckHostIP=no',
                'GlobalKnownHostsFile=/dev/null',
                'UserKnownHostsFile=/dev/null',
                'StrictHostKeyChecking=no',
                'LogLevel=quiet',
            ]
            ssh_args = reduce(lambda acc, opt: acc + ['-o', opt],
                              ssh_options, [])
            cmd = ['ssh'] + ssh_args + ["root@{0}".format(self.server.ip)]
            env = dict(os.environ)
            env['DISPLAY'] = ":666"
            env['SSH_ASKPASS'] = askpass
            subprocess.check_call(cmd, env=env, preexec_fn=os.setsid)

        self.observed_deactivate(*args, **kwargs)


class Server(object):
    def __init__(self, conn, result):
        self.conn = conn
        self.update_info(result)
        self.rescue = RescueSystem(self)

    def update_info(self, result=None):
        """
        Updates the information of the current Server instance either by
        sending a new GET request or by parsing the response given by result.
        """
        if result is None:
            result = self.conn.get('/server/{0}'.format(self.ip))

        data = result['server']

        self.ip = data['server_ip']
        self.name = data['server_name']
        self.product = data['product']
        self.datacenter = data['dc']
        self.traffic = data['traffic']
        self.flatrate = data['flatrate']
        self.status = data['status']
        self.throttled = data['throttled']
        self.cancelled = data['cancelled']
        self.paid_until = datetime.strptime(data['paid_until'], '%Y-%m-%d')

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
            tries = ['soft', 'hard']

        for mode in tries:
            self.reboot(mode)

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
        """
        modes = {
            'manual': 'man',
            'hard': 'hw',
            'soft': 'sw',
        }

        modekey = modes.get(mode, modes['soft'])
        return self.conn.post('/reset/{0}'.format(self.ip), {'type': modekey})

    def __repr__(self):
        return "<{0} ({1})>".format(self.ip, self.product)
