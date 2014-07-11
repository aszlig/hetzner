import socket
import struct


def parse_ipv4(addr):
    """
    Return a numeric representation of the given IPv4 address.
    """
    binary_ip = socket.inet_pton(socket.AF_INET, addr)
    return struct.unpack('!L', binary_ip)[0]


def parse_ipv6(addr):
    """
    Return a numeric representation of the given IPv6 address.
    """
    binary_ip = socket.inet_pton(socket.AF_INET6, addr)
    high, low = struct.unpack('!QQ', binary_ip)
    return high << 64 | low


def parse_ipaddr(addr, is_ipv6=None):
    """
    Parse IP address and return a tuple consisting of a boolean indicating
    whether the given address is an IPv6 address and the numeric representation
    of the address.

    If is_ipv6 is either True or False, the specific address type is enforced
    and only the parsed address is returned instead of a tuple.
    """
    if is_ipv6 is None:
        try:
            return False, parse_ipv4(addr)
        except socket.error:
            return True, parse_ipv6(addr)
    elif is_ipv6:
        return parse_ipv6(addr)
    else:
        return parse_ipv4(addr)


def get_ipv4_range(numeric_netaddr, prefix_len):
    """
    Return the smallest and biggest possible IPv4 address of the specified
    network address (in numeric representation) and prefix length.
    """
    mask_inverted = 32 - prefix_len
    mask_bin = 0xffffffff >> mask_inverted << mask_inverted
    range_start = numeric_netaddr & mask_bin
    range_end = range_start | (1 << mask_inverted) - 1
    return range_start, range_end


def get_ipv6_range(numeric_netaddr, prefix_len):
    """
    Return the smallest and biggest possible IPv6 address of the specified
    network address (in numeric representation) and prefix length.
    """
    mask_bin_full = 0xffffffffffffffffffffffffffffffff
    mask_inverted = 128 - prefix_len
    mask_bin = mask_bin_full >> mask_inverted << mask_inverted
    range_start = numeric_netaddr & mask_bin
    range_end = range_start | (1 << mask_inverted) - 1
    return range_start, range_end


def ipv4_bin2addr(numeric_addr):
    """
    Convert a numeric representation of the given IPv4 address into quad-dotted
    notation.
    """
    packed = struct.pack('!L', numeric_addr)
    return socket.inet_ntop(socket.AF_INET, packed)


def ipv6_bin2addr(numeric_addr):
    """
    Convert a numeric representation of the given IPv6 address into a shortened
    hexadecimal notiation separated by colons.
    """
    high = numeric_addr >> 64
    low = numeric_addr & 0xffffffffffffffff
    packed = struct.pack('!QQ', high, low)
    return socket.inet_ntop(socket.AF_INET6, packed)
