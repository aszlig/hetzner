import unittest
import struct
import socket

from hetzner.util.addr import (parse_ipv4, parse_ipv6, parse_ipaddr,
                               get_ipv4_range, get_ipv6_range,
                               ipv4_bin2addr, ipv6_bin2addr)


class UtilAddrTestCase(unittest.TestCase):
    def test_parse_ipv4(self):
        self.assertEqual(parse_ipv4('174.26.72.88'), 2920958040)
        self.assertEqual(parse_ipv4('0.0.0.0'), 0)
        self.assertEqual(parse_ipv4('255.255.255.255'), 4294967295)
        self.assertRaises(socket.error, parse_ipv4, '999.999.999.999')
        self.assertRaises(socket.error, parse_ipv4, '::ffff:192.168.0.1')

    def test_parse_ipv6(self):
        self.assertEqual(parse_ipv6('::ffff:192.168.0.1'), 281473913978881)
        self.assertEqual(parse_ipv6('fe80::fbd6:7860'),
                         338288524927261089654018896845572831328)
        self.assertEqual(parse_ipv6('ffff:ffff:ffff:ffff:ffff:ffff:ffff:ffff'),
                         340282366920938463463374607431768211455)
        self.assertEqual(parse_ipv6('::'), 0)
        self.assertRaises(socket.error, parse_ipv6, '174.26.72.88')

    def test_parse_ipaddr(self):
        self.assertEqual(parse_ipaddr('1.2.3.4'), (False, 16909060))
        self.assertEqual(parse_ipaddr('255.255.0.0', False), 4294901760)
        self.assertEqual(parse_ipaddr('dead::beef'),
                         (True, 295986882420777848964380943247191621359))
        self.assertEqual(parse_ipaddr('ffff::ffff', True),
                         340277174624079928635746076935439056895)
        self.assertRaises(socket.error, parse_ipaddr, '1.2.3.4', True)
        self.assertRaises(socket.error, parse_ipaddr, 'dead::beef', False)
        self.assertRaises(socket.error, parse_ipaddr, 'invalid')

    def test_get_ipv4_range(self):
        self.assertEqual(get_ipv4_range(0xac100000, 12),
                         (2886729728, 2887778303))
        self.assertEqual(get_ipv4_range(0xa1b2c3d4, 16),
                         (2712797184, 2712862719))
        self.assertEqual(get_ipv4_range(0xa1b2c3d4, 32),
                         (2712847316, 2712847316))
        self.assertEqual(get_ipv4_range(0xa1b2c3d4, 0),
                         (0, 4294967295))
        self.assertRaises(ValueError, get_ipv4_range, 0x01, 64)

    def test_get_ipv6_range(self):
        self.assertEqual(
            get_ipv6_range(0x00010203ff05060708091a1b1c1d1e1f, 36),
            (5233173638632030885207665411096576,
             5233178590392188026728765007593471)
        )
        self.assertEqual(
            get_ipv6_range(0x000102030405060708091a1b1c1d1e1f, 64),
            (5233100606242805471950326074441728,
             5233100606242823918694399783993343)
        )
        self.assertEqual(
            get_ipv6_range(0x000102030405060708091a1b1c1d1e1f, 128),
            (5233100606242806050973056906370591,
             5233100606242806050973056906370591)
        )
        self.assertEqual(
            get_ipv6_range(0x000102030405060708091a1b1c1d1e1f, 0),
            (0, 340282366920938463463374607431768211455)
        )
        self.assertRaises(ValueError, get_ipv6_range, 0x01, 256)

    def test_ipv4_bin2addr(self):
        self.assertEqual(ipv4_bin2addr(0x01020304), '1.2.3.4')
        self.assertEqual(ipv4_bin2addr(0x0000ffff), '0.0.255.255')
        self.assertEqual(ipv4_bin2addr(0xffff0000), '255.255.0.0')
        self.assertRaises(struct.error, ipv4_bin2addr, 0xa1ffff0000)

    def test_ipv6_bin2addr(self):
        self.assertEqual(ipv6_bin2addr(0x01020304050607080910111213141516),
                         '102:304:506:708:910:1112:1314:1516')
        self.assertEqual(ipv6_bin2addr(0xffff000000000dead00000beef000000),
                         'ffff::dea:d000:be:ef00:0')
        self.assertEqual(ipv6_bin2addr(0x123400000000000000000000000000ff),
                         '1234::ff')
        self.assertRaises(struct.error, ipv6_bin2addr,
                          0xa1ffff0000000000000000000000000000)
