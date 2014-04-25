import socket
import struct


def parse_ipv4(addr):
    """
    Return a numeric representation of the given IPv4 address.

    >>> parse_ipv4('174.26.72.88')
    2920958040
    >>> parse_ipv4('0.0.0.0')
    0
    >>> parse_ipv4('255.255.255.255')
    4294967295
    >>> parse_ipv4('999.999.999.999')
    Traceback (most recent call last):
        ...
    error: illegal IP address string passed to inet_pton
    >>> parse_ipv4('::ffff:192.168.0.1')
    Traceback (most recent call last):
        ...
    error: illegal IP address string passed to inet_pton
    """
    binary_ip = socket.inet_pton(socket.AF_INET, addr)
    return struct.unpack('!L', binary_ip)[0]


def parse_ipv6(addr):
    """
    Return a numeric representation of the given IPv6 address.

    >>> parse_ipv6('::ffff:192.168.0.1')
    281473913978881
    >>> parse_ipv6('fe80::fbd6:7860')
    338288524927261089654018896845572831328L
    >>> parse_ipv6('ffff:ffff:ffff:ffff:ffff:ffff:ffff:ffff')
    340282366920938463463374607431768211455L
    >>> parse_ipv6('::')
    0
    >>> parse_ipv6('174.26.72.88')
    Traceback (most recent call last):
        ...
    error: illegal IP address string passed to inet_pton
    """
    binary_ip = socket.inet_pton(socket.AF_INET6, addr)
    high, low = struct.unpack('!QQ', binary_ip)
    return high << 64 | low


def parse_ipaddr(addr, is_ipv6=None):
    """
    Parse IP address and return a tuple consisting of a boolean indicating
    whether the given address is an IPv6 address and the numeric representation
    of the address.

    If is_ipv6 is either True or False, the specific address type is enforced.

    >>> parse_ipaddr('1.2.3.4')
    (False, 16909060)
    >>> parse_ipaddr('255.255.0.0', False)
    (False, 4294901760)
    >>> parse_ipaddr('dead::beef')
    (True, 295986882420777848964380943247191621359L)
    >>> parse_ipaddr('ffff::ffff', True)
    (True, 340277174624079928635746076935439056895L)
    >>> parse_ipaddr('1.2.3.4', True)
    Traceback (most recent call last):
        ...
    error: illegal IP address string passed to inet_pton
    >>> parse_ipaddr('dead::beef', False)
    Traceback (most recent call last):
        ...
    error: illegal IP address string passed to inet_pton
    >>> parse_ipaddr('invalid')
    Traceback (most recent call last):
        ...
    error: illegal IP address string passed to inet_pton
    """
    if is_ipv6 is None:
        try:
            return False, parse_ipv4(addr)
        except socket.error:
            return True, parse_ipv6(addr)
    elif is_ipv6:
        return True, parse_ipv6(addr)
    else:
        return False, parse_ipv4(addr)
