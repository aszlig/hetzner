try:
    from urllib import urlencode
except ImportError:
    from urllib.parse import urlencode

import datetime

from hetzner import RobotError

__all__ = ["VirtualSwitch", "VirtualSwitchManager"]


class VirtualSwitch:
    def __init__(self, conn):
        """_summary_

        Args:
            conn (_type_): _description_
        """
        self.conn = conn
        self.ip = ip
        self.update_info(result)

    def update_info(self, result=None):
        if result is None:
            try:
                result = self.conn.get(f"/vswitch/{self.ip}")
            except RobotError as err:
                if err.status == 404:
                    result = None
                else:
                    raise

        if result is not None:

            self.id = result["id"]
            self.name = result["name"]
            self.vlan = result["vlan"]
            self.cancelled = result["cancelled"]
        else:
            self.id = None

    def set(self, name: str):
        self.conn.post(f"/vswitch/{self.id}", {"name": name}, True)

    def create(self, name: str, vlan: str):
        self.conn.post("/vswitch", {"name": name, "vlan": vlan}, True)

    def remove(self, id):

        # This requires the date of removal.
        self.conn.delete(
            f"/vswitch/{id}",
            {"cancellation_date": datetime.datetime.now().strftime("%Y-%m-%d")},
        )

    def __repr__(self):
        return f"<VirtualSwitch ID: {self.id}>"


class VirtualSwitchManager:
    def __init__(self, conn, switch_id=None):
        self.conn = conn
        self.switch_id = switch_id

    def get(self, id):
        return VirtualSwitch(self.conn, id)

    def create(self, name, vlan):
        return VirtualSwitch(self.conn).create(name, vlan)

    def delete(self, id):
        return VirtualSwitch(self.conn).remove(id)

    def __iter__(self):
        if self.switch_id is None:
            url = "/vswitch"
        else:
            data = urlencode({"switch_id": self.switch_id})
            url = f"/vswitch?{data}"
        try:
            result = self.conn.get(url)
        except RobotError as err:
            if err.status == 404:
                result = []
            else:
                raise
        return iter([VirtualSwitch(self.conn, result=vswitch) for vswitch in result])
