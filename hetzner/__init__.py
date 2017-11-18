class RobotError(Exception):
    def __init__(self, message, status=None):
        if status is not None:
            message = "{0} ({1})".format(message, status)
        super(RobotError, self).__init__(message)
        self.status = status


class ManualReboot(Exception):
    pass


class ConnectError(Exception):
    pass


class WebRobotError(RobotError):
    pass
