class RobotError(Exception):
    def __init__(self, message, status=None):
        if status is not None:
            message = f"{message} ({status})"
        super().__init__(message)
        self.status = status


class ManualReboot(Exception):
    pass


class ConnectError(Exception):
    pass


class WebRobotError(RobotError):
    pass
