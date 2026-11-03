# Tencent is pleased to support the open source community by making tRPC-Metrics-Runtime available.
#
# Copyright (C) 2026 Tencent. All rights reserved.
#
# tRPC-Metrics-Runtime is licensed under Apache-2.0.
"""Fallback IP and container identity for the stat payload.

Config is preferred. When it is missing, Docker uses pod environment
variables and a host process walks NICs. Values that fail ``is_ip_valid``
are skipped.
"""

import os

import netifaces

from trpc_sdk.config import TrpcConfig
from trpc_sdk.utils import get_ip_with_nic

from .utils import is_in_docker
from .utils import is_ip_valid


def _try_get_ip_from_config() -> str:
    """Return the first usable IP recorded in the loaded tRPC config.

    Order is global ``local_ip``, then each service ``ip``, then the address
    of each service NIC. The first value accepted by ``is_ip_valid`` wins.

    Returns:
        A usable address, or an empty string when config has none.
    """
    # Prefer the address the process already published in global config.
    global_config = TrpcConfig.global_config()
    if global_config:
        if is_ip_valid(global_config.local_ip):
            return global_config.local_ip

    # Then a service listen address.
    server_config = TrpcConfig.server_config()
    if server_config and server_config.service:
        for service in server_config.service:
            if is_ip_valid(service.ip):
                return service.ip

    # Then the address of the NIC named by a service.
    if server_config and server_config.service:
        for service in server_config.service:
            ip = get_ip_with_nic(service.nic)
            if is_ip_valid(ip):
                return ip

    return ""


def _get_default_ip_slow() -> str:
    """Return the first usable address found by walking local NICs.

    IPv4 is preferred over IPv6. The first address of each family that
    passes ``is_ip_valid`` is kept. Interface lookup errors yield an empty
    string instead of failing the report.

    Returns:
        A usable IPv4 address, else a usable IPv6 address, else ``""``.
    """
    ipv4 = ""
    ipv6 = ""
    try:
        for nic in netifaces.interfaces():
            nic_addrs = netifaces.ifaddresses(nic)
            if netifaces.AF_INET in nic_addrs and len(ipv4) == 0:
                tmp_ip = nic_addrs[netifaces.AF_INET][0]["addr"]
                if is_ip_valid(tmp_ip):
                    ipv4 = tmp_ip
            elif netifaces.AF_INET6 in nic_addrs and len(ipv6) == 0:
                tmp_ip = nic_addrs[netifaces.AF_INET6][0]["addr"]
                if is_ip_valid(tmp_ip):
                    ipv6 = tmp_ip
    except Exception:  # pylint: disable=broad-except
        pass
    if ipv4:
        return ipv4
    if ipv6:
        return ipv6
    return ""


def _get_default_ip_from_host() -> str:
    """Return this host's report address outside a container.

    Config is checked before the NIC walk so an explicitly configured address
    is not replaced by whichever interface ``netifaces`` lists first.

    Returns:
        A usable address, or an empty string when neither source has one.
    """
    ip = _try_get_ip_from_config()
    if len(ip) > 0:
        return ip
    return _get_default_ip_slow()


def get_default_ip() -> str:
    """Return the IP to put in a stat payload when config did not supply one.

    Inside Docker the only accepted source is the ``NODE_IP`` environment
    variable, and only when ``is_ip_valid`` accepts it. A container without
    that variable reports an empty IP rather than a bridge address. Outside
    Docker, config and then local NICs are used.

    Returns:
        A usable address, or an empty string.
    """
    if is_in_docker():
        # Do not fall through to a container bridge address from the NIC walk.
        if "NODE_IP" in os.environ and is_ip_valid(os.environ["NODE_IP"]):
            return os.environ["NODE_IP"]
        return ""

    return _get_default_ip_from_host()


def _try_get_container_from_env() -> str:
    """Build a container id from the Kubernetes downward environment.

    All three of ``CLUSTER_ID``, ``POD_NAMESPACE``, and ``POD_NAME`` must be
    set. A partial set is treated as missing so the payload does not mix
    identifiers from different sources.

    Returns:
        ``CLUSTER_ID/POD_NAMESPACE/POD_NAME``, or an empty string.
    """
    envs = ["CLUSTER_ID", "POD_NAMESPACE", "POD_NAME"]
    if any(map(lambda env: env not in os.environ, envs)):
        return ""

    return "/".join(map(lambda env: os.environ[env], envs))


def get_default_container() -> str:
    """Return the container name to put in a stat payload.

    Non-Docker processes have no container identity and return an empty
    string. Inside Docker the pod env triple is preferred. If it is absent,
    the host or overlay IP is used as a stand-in name so the stat service
    can still tell instances apart.

    Returns:
        A container id, a fallback address, or an empty string.
    """
    if not is_in_docker():
        # A host process is identified by IP alone.
        return ""

    container = _try_get_container_from_env()
    if len(container) > 0:
        return container

    # Last resort: distinguish this instance by the overlay or node address.
    return _get_default_ip_from_host()
