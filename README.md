Python API for the Hetzner Robot
================================

API usage
---------

This is a small example session to illustrate how to use the API:

```python
>>> from hetzner.robot import Robot
>>> robot = Robot("username", "password")
>>> list(robot.servers)
[<Server1>, <Server2>, <Server3>, <Server4>]
>>> server = robot.servers.get("1.2.3.4")
>>> server.status
u'ready'
>>> server.name
u'shiny server'
>>> server.reboot(mode='hard')
<httplib.HTTPResponse instance at 0x90d5a8>
>>> list(server.ips)
[<IpAddress 1.2.3.4>]
>>> server.set_name("foobar")
>>> server.name
u'foobar'
>>>
>>> server.rescue.shell()
Linux rescue 3.10.25 #128 SMP Tue Jan 7 10:58:27 CET 2014 x86_64

-------------------------------------------------------------------

  Welcome to the Hetzner Rescue System.

  This Rescue System is based on Debian 7.0 (wheezy) with a newer
  kernel. You can install software as in a normal system.

  To install a new operating system from one of our prebuilt
  images, run 'installimage' and follow the instructions.

  More information at http://wiki.hetzner.de

-------------------------------------------------------------------

Hardware data:
   ...

Network data:
   ...

root@rescue ~ # logout
>>> server.rescue.active
False
>>>
```

Commandline helper tool
-----------------------

There is also a small commandline helper tool called `hetznerctl`, which exposes
most of the API functionality in a CLI similar to popular SCMs like Git or SVN.

In order to show the available commands type `hetznerctl --help`.
Every subcommand has its own help, like for example `hetznerctl rescue --help`.
