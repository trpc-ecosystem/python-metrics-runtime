# Tencent is pleased to support the open source community by making tRPC-Metrics-Runtime available.
#
# Copyright (C) 2026 Tencent. All rights reserved.
#
# tRPC-Metrics-Runtime is licensed under Apache-2.0.
"""Address and environment checks used when filling a report payload.

A report must not advertise a loopback, link-local, or private address as the
service IP. Docker detection decides whether container identity comes from
pod environment variables.
"""

import ipaddress
import os.path


def is_ip_valid(ip_str: str) -> bool:
    """Return whether ``ip_str`` can be sent as this process's service address.

    Empty input and values that ``ipaddress`` cannot parse are rejected.
    Unspecified (``0.0.0.0``, ``::``), loopback (``127.0.0.0/8``, ``::1``),
    and link-local (``169.254.0.0/16``, ``fe80::/10``) addresses are rejected.
    IPv4 private ranges ``172.16.0.0/12`` and ``192.168.0.0/16`` are rejected.
    IPv6 unique-local ``FC00::/7`` and site-local ``FEC0::/10`` are rejected.
    ``10.0.0.0/8`` is not in the rejected set.

    Args:
        ip_str: Candidate address from config, an environment variable, or a NIC.

    Returns:
        True when the address is usable in a stat payload.
    """
    if not ip_str:
        return False
    try:
        ip = ipaddress.ip_address(ip_str)
    except ValueError:
        return False

    if ip.is_unspecified:
        # 0.0.0.0 and :: are not bound service addresses.
        return False
    if ip.is_loopback:
        # 127.0.0.0/8 and ::1 stay on this host.
        return False
    if ip.is_link_local:
        # 169.254.0.0/16 and fe80::/10 are not routable service addresses.
        return False
    if isinstance(ip, ipaddress.IPv4Address):
        if any(
                map(lambda net: ip in net, [
                    ipaddress.IPv4Network("172.16.0.0/12"),
                    ipaddress.IPv4Network("192.168.0.0/16"),
                ])):
            return False
    elif isinstance(ip, ipaddress.IPv6Address):
        if any(map(lambda net: ip in net, [
                ipaddress.IPv6Network("FC00::/7"),
                ipaddress.IPv6Network("FEC0::/10"),
        ])):
            return False
    else:
        return False
    return True


def is_in_docker() -> bool:
    """Return whether this process appears to run inside a Docker container.

    The check is only the presence of ``/.dockerenv``. It does not inspect
    cgroup or Kubernetes downward API files.

    Returns:
        True when ``/.dockerenv`` exists.
    """
    return os.path.isfile("/.dockerenv")
