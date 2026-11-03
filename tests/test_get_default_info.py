# Tencent is pleased to support the open source community by making tRPC-Metrics-Runtime available.
#
# Copyright (C) 2026 Tencent. All rights reserved.
#
# tRPC-Metrics-Runtime is licensed under Apache-2.0.
""" Test get default info"""

from unittest import mock

import netifaces

from trpc_metrics_runtime.get_default_info import get_default_ip, get_default_container
from .utils import FakeTrpcConfig


@mock.patch("os.path.isfile", return_value=True)
@mock.patch("os.environ", {"NODE_IP": "1.2.3.4"})
def test_get_default_ip_from_env(isfile):
    """Test get default ip from env"""
    assert get_default_ip() == "1.2.3.4"


@mock.patch("os.path.isfile", return_value=True)
@mock.patch("os.environ", {})
def test_get_default_ip_from_env_failed(isfile):
    """Test get default ip from env failed"""
    assert get_default_ip() == ""


@mock.patch("os.path.isfile", return_value=False)
@mock.patch("trpc_metrics_runtime.get_default_info.TrpcConfig", new_callable=FakeTrpcConfig)
def test_get_default_ip_from_global_ip(config_obj, isfile):
    """Test get default ip from global ip"""
    config_obj.global_config.local_ip = "2.3.4.5"
    assert get_default_ip() == "2.3.4.5"


@mock.patch("os.path.isfile", return_value=False)
@mock.patch("trpc_metrics_runtime.get_default_info.TrpcConfig", new_callable=FakeTrpcConfig)
def test_get_default_ip_from_service_ip(config_obj, isfile):
    """Test get default ip from service ip"""
    config_obj.global_config.local_ip = "0.0.0.0"
    config_obj.server.service = [mock.MagicMock()]
    config_obj.server.service[0].ip = "3.4.5.6"
    assert get_default_ip() == "3.4.5.6"


@mock.patch("os.path.isfile", return_value=False)
@mock.patch("trpc_metrics_runtime.get_default_info.TrpcConfig", new_callable=FakeTrpcConfig)
@mock.patch("trpc_metrics_runtime.get_default_info.get_ip_with_nic")
def test_get_default_ip_from_service_nic(get_ip_with_nic, config_obj, isfile):
    """Test get default ip from service nic"""

    def f(nic: str) -> str:
        if nic == "eth233":
            return "4.5.6.7"
        raise ValueError

    get_ip_with_nic.side_effect = f
    config_obj.global_config.local_ip = "0.0.0.0"
    config_obj.server.service = [mock.MagicMock()]
    config_obj.server.service[0].ip = "0.0.0.0"
    config_obj.server.service[0].nic = "eth233"
    assert get_default_ip() == "4.5.6.7"


@mock.patch("os.path.isfile", return_value=False)
@mock.patch("trpc_metrics_runtime.get_default_info.TrpcConfig", new_callable=FakeTrpcConfig)
@mock.patch("trpc_metrics_runtime.get_default_info.get_ip_with_nic")
@mock.patch("netifaces.interfaces", return_value=["eth7"])
@mock.patch("netifaces.ifaddresses")
def test_get_default_ip_from_ipv4_interface(ifaddresses, interfaces, get_ip_with_nic, config_obj, isfile):
    """Test get default ip from ipv4 interface"""

    def f(nic: str) -> str:
        if nic == "lo":
            return "127.0.0.1"
        raise ValueError

    get_ip_with_nic.side_effect = f

    def g(nic: str) -> str:
        if nic == "eth7":
            return {netifaces.AF_INET: [{"addr": "5.6.7.8"}]}
        raise ValueError

    ifaddresses.side_effect = g
    config_obj.server.service = [mock.MagicMock()]
    config_obj.server.service[0].ip = "0.0.0.0"
    config_obj.server.service[0].nic = "lo"
    assert get_default_ip() == "5.6.7.8"


@mock.patch("os.path.isfile", return_value=False)
@mock.patch("trpc_metrics_runtime.get_default_info.TrpcConfig", new_callable=FakeTrpcConfig)
@mock.patch("trpc_metrics_runtime.get_default_info.get_ip_with_nic")
@mock.patch("netifaces.interfaces", return_value=["eth7"])
@mock.patch("netifaces.ifaddresses")
def test_get_default_ip_from_ipv6_interface(ifaddresses, interfaces, get_ip_with_nic, config_obj, isfile):
    """Test get default ip from ipv6 interface"""

    def f(nic: str) -> str:
        if nic == "lo":
            return "127.0.0.1"
        raise ValueError

    get_ip_with_nic.side_effect = f

    def g(nic: str) -> str:
        if nic == "eth7":
            return {netifaces.AF_INET6: [{"addr": "::67:89:ab:cd"}]}
        raise ValueError

    ifaddresses.side_effect = g
    config_obj.server.service = [mock.MagicMock()]
    config_obj.server.service[0].ip = "0.0.0.0"
    config_obj.server.service[0].nic = "lo"
    assert get_default_ip() == "::67:89:ab:cd"


@mock.patch("os.path.isfile", return_value=False)
@mock.patch("trpc_metrics_runtime.get_default_info.TrpcConfig", new_callable=FakeTrpcConfig)
@mock.patch("trpc_metrics_runtime.get_default_info.get_ip_with_nic")
@mock.patch("netifaces.interfaces", side_effect=PermissionError)
@mock.patch("netifaces.ifaddresses")
def test_get_default_ip_from_interface_failed(ifaddresses, interfaces, get_ip_with_nic, config_obj, isfile):
    """Test get default ip from interface failed"""

    def f(nic: str) -> str:
        if nic == "lo":
            return "127.0.0.1"
        raise ValueError

    get_ip_with_nic.side_effect = f
    config_obj.server.service = [mock.MagicMock()]
    config_obj.server.service[0].ip = "0.0.0.0"
    config_obj.server.service[0].nic = "lo"
    assert get_default_ip() == ""
    ifaddresses.assert_not_called()


@mock.patch("os.path.isfile", return_value=False)
def test_get_default_container_without_dockerenv(isfile):
    """Test get default container without dockerenv"""
    assert get_default_container() == ""


@mock.patch("os.path.isfile", return_value=True)
@mock.patch("os.environ", {"CLUSTER_ID": "c", "POD_NAMESPACE": "n", "POD_NAME": "p"})
def test_get_default_container_from_environ(isfile):
    """Test get default container from environ"""
    assert get_default_container() == "c/n/p"


@mock.patch("os.path.isfile", return_value=True)
@mock.patch("os.environ", {})
@mock.patch("trpc_metrics_runtime.get_default_info.TrpcConfig", new_callable=FakeTrpcConfig)
def test_get_default_container_replaced_by_config(config_obj, isfile):
    """Test get default container replaced by config"""
    config_obj.global_config.local_ip = "7.8.9.10"
    assert get_default_container() == "7.8.9.10"


@mock.patch("os.path.isfile", return_value=True)
@mock.patch("os.environ", {})
@mock.patch("trpc_metrics_runtime.get_default_info._get_default_ip_slow")
def test_get_default_container_replaced_by_interfaces(get_default_ip_slow, isfile):
    """Test get default container replaced by interfaces"""
    get_default_ip_slow.return_value = "8.9.10.11"
    assert get_default_container() == "8.9.10.11"
    get_default_ip_slow.assert_called_once()
