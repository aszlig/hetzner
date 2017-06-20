class RobotError(Exception):
    def __init__(self, message, status=None):
        formattedMessage = message if status is None else "{0} ({1})".format(message, status)
        super(Exception, self).__init__(formattedMessage)
        self.status = status


class ManualReboot(Exception):
    pass


class ConnectError(Exception):
    pass


class WebRobotError(RobotError):
    pass
