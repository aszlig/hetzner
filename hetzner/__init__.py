class RobotError(Exception):
    def __init__(self, message, status=None):
        if status is None:
            self.message = message
        else:
            self.message = "{0} ({1})".format(message, status)
        self.status = status


class ManualReboot(Exception):
    pass


class ConnectError(Exception):
    pass


class WebRobotError(RobotError):
    pass
