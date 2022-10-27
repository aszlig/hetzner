import socket
import time

from hetzner import ConnectError, ManualReboot


class Reset(object):
    def __init__(self, server):
        self.server = server
        self.conn = server.conn

        self._reset_types = None
        self._operating_status = None

    def _update_status(self):
        data = self.conn.get('/reset/{0}'.format(self.server.number))
        self._operating_status = data['reset']['operating_status']
        self._reset_types = data['reset']['type']

    @property
    def is_running(self):
        """
        Whether the server is running or powered off. If querying the status
        is unsupported for the server, None is returned.
        """
        return {'running': True, 'shut off': False}.get(self.operating_status)

    @property
    def operating_status(self):
        """
        The current operating status of the server.
        """
        # Don't cache the result, because the status might have changed
        # in the meantime.
        self._update_status()
        return self._operating_status

    @property
    def reset_types(self):
        """
        The reset types available for this server.
        """
        if self._reset_types is None:
            self._update_status()
        return self._reset_types

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
            s.connect((self.server.ip, port))
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
            self.server.logger.info("Trying to reboot using the %r method.",
                                    mode)
            self.reboot(mode)

            start_time = time.time()
            self.server.logger.info("Waiting for machine to become available.")
            while True:
                current_time = time.time()
                if current_time > start_time + patience:
                    self.server.logger.info(
                        "Machine didn't come up after %d seconds.",
                        patience
                    )
                    break

                is_up = self.check_ssh()
                time.sleep(1)

                if is_up and is_down:
                    self.server.logger.info("Machine just became available.")
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
            'power': 'power',
        }

        modekey = modes.get(mode, modes['soft'])
        return self.conn.post('/reset/{0}'.format(self.server.number),
                              {'type': modekey})
