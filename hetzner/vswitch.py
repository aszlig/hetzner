#!/usr/bin/env python3
# ----------------------------------------------------------------------------
# Created By   : Wieger Bontekoe <wieger.bontekoe@productsup.com>
# Created Date : 2023-01-13
#
# Copyright (c) 2023, Products Up GmbH
#
# All rights reserved.
# Unauthorized copying of this file, via any medium is strictly prohibited.
#
# ---------------------------------------------------------------------------
""" vSwitch implementation for Hetzner """
# ---------------------------------------------------------------------------
# Imports from here.
# ---------------------------------------------------------------------------
#
#
# from hetzner.robot import Robot
#
# conn = Robot("username", "password")
#
# Create new vSwitch
# conn.vswitch.create("wieger", 4000)
#
# Loop through vSwitches
# for switch in conn.vswitch:
#
#    # print out some var
#    print(switch.id)
#    print(switch.name)
#    print(switch.vlan)
#
#
# Get a single vSwitch
# s = conn.vswitch.get(36585)
# print(s.id)

# Delete a single vSwitch
# conn.vswitch.delete(id)


try:
    from urllib import urlencode
except ImportError:
    from urllib.parse import urlencode

import datetime

from hetzner import RobotError

__all__ = ["VirtualSwitch", "VirtualSwitchManager"]


class VirtualSwitch:
    def __init__(self, conn, result=None):
        """_summary_

        Args:
            conn (_type_): _description_
        """
        self.conn = conn
        self.id = id
        self.update_info(result)

    def update_info(self, result=None):

        if result is not None:

            self.id = result["id"]
            self.name = result["name"]
            self.vlan = result["vlan"]
            self.cancelled = result["cancelled"]
            
            if result["subnet"]:
                self.subnet = result["subnet"]
            else:
                self.subnet = None
               
            if result["server"]:
                self.server = result["server"]
            else:
                self.server = None
            
            if result["cloud_network"]:
                self.cloud_network = result["cloud_network"]
            else:
                self.cloud_network = None
            
        else:
            self.id = None

    def get(self, id: int):
        result = self.conn.get(f"/vswitch/{id}")
        self.update_info(result)
        return self

    def set(self, name: str):
        self.conn.post(f"/vswitch/{self.id}", {"name": name}, True)

    def create(self, name: str, vlan: str):

        self.conn.post("/vswitch", {"name": name, "vlan": vlan}, True)

    def remove(self, id: int):

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

    def get(self, id: int):
        return VirtualSwitch(self.conn).get(id)

    def create(self, name: str, vlan: int):
        return VirtualSwitch(self.conn).create(name, vlan)

    def delete(self, id: int):
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
