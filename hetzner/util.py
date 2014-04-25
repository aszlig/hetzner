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


def get_ipv4_range(numeric_netaddr, prefix_len):
    """
    Return the smallest and biggest possible IPv4 address of the specified
    network address (in numeric representation) and prefix length.

    The range doesn't include the broadcast address.

    >>> get_ipv4_range(0xac100000, 12)
    (2886729728, 2887778302)
    >>> get_ipv4_range(0xa1b2c3d4, 16)
    (2712797184, 2712862718)
    >>> get_ipv4_range(0xa1b2c3d4, 32)
    (2712847316, 2712847316)
    >>> get_ipv4_range(0xa1b2c3d4, 0)
    (0, 4294967294)
    >>> get_ipv4_range(0x01, 64)
    Traceback (most recent call last):
        ...
    ValueError: negative shift count
    """
    mask_inverted = 32 - prefix_len
    mask_bin = 0xffffffff >> mask_inverted << mask_inverted
    range_start = numeric_netaddr & mask_bin
    range_end = range_start | (1 << mask_inverted) - 1
    return range_start, max(range_start, range_end - 1)


def get_ipv6_range(numeric_netaddr, prefix_len):
    """
    Return the smallest and biggest possible IPv6 address of the specified
    network address (in numeric representation) and prefix length.

    >>> get_ipv6_range(0x00010203ff05060708091a1b1c1d1e1f, 36)
    (5233173638632030885207665411096576L, 5233178590392188026728765007593471L)
    >>> get_ipv6_range(0x000102030405060708091a1b1c1d1e1f, 64)
    (5233100606242805471950326074441728L, 5233100606242823918694399783993343L)
    >>> get_ipv6_range(0x000102030405060708091a1b1c1d1e1f, 128)
    (5233100606242806050973056906370591L, 5233100606242806050973056906370591L)
    >>> get_ipv6_range(0x000102030405060708091a1b1c1d1e1f, 0)
    (0L, 340282366920938463463374607431768211455L)
    >>> get_ipv6_range(0x01, 256)
    Traceback (most recent call last):
        ...
    ValueError: negative shift count
    """
    mask_bin_full = 0xffffffffffffffffffffffffffffffff
    mask_inverted = 128 - prefix_len
    mask_bin = mask_bin_full >> mask_inverted << mask_inverted
    range_start = numeric_netaddr & mask_bin
    range_end = range_start | (1 << mask_inverted) - 1
    return range_start, range_end
