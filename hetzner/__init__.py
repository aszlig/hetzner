class RobotError(Exception):
    def __init__(self, message, status=None):
        self.message = message
        self.status = status

    def __repr__(self):
        if self.status is None:
            return self.message
        else:
            return "{0} ({1})".format(self.message, self.status)


class ManualReboot(Exception):
    pass


class ConnectError(Exception):
    pass


class WebRobotError(RobotError):
    pass
