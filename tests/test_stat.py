# Tencent is pleased to support the open source community by making tRPC-Metrics-Runtime available.
#
# Copyright (C) 2026 Tencent. All rights reserved.
#
# tRPC-Metrics-Runtime is licensed under Apache-2.0.
""" Test stat"""
from unittest import mock

import pytest

from trpc_metrics_runtime.constants import STAT_DOMAIN
from trpc_metrics_runtime.constants import REPORT_LIMITED
from trpc_metrics_runtime.constants import REPORT_REPEAT
from trpc_metrics_runtime.constants import RESP_FORBIDDEN
from trpc_metrics_runtime.constants import RESP_OK
from trpc_metrics_runtime.constants import STAT_URI
from trpc_metrics_runtime.constants import STATS_URI
from trpc_metrics_runtime.stat import Client
from .utils import DUMMY_PLUGIN_SPECS, FakeTrpcConfig, SERVER


@pytest.mark.asyncio
async def test_report_plugin():
    """Test the old single plugin report"""
    client = Client(server=SERVER)
    with mock.patch.object(Client, "post", return_value=(RESP_OK, "")) as post:
        assert await client.stat("runtime", "0.0.5")

    url, payload = post.call_args.args[:2]
    assert url == f"http://{STAT_DOMAIN}/{STAT_URI}"
    assert payload["plugin"] == "runtime"
    assert payload["version"] == "0.0.5"
    await client.close()


@pytest.mark.asyncio
async def test_report_plugins_once():
    """Test the batch report"""
    client = Client(server=SERVER)
    plugins = [{s.plugin_name: s.version} for s in DUMMY_PLUGIN_SPECS if s.report]
    with mock.patch.object(Client, "post", return_value=(RESP_OK, "")) as post:
        assert await client.stats("0.1.11", plugins)

    url, payload = post.call_args.args[:2]
    assert url == f"http://{STAT_DOMAIN}/{STATS_URI}"
    assert payload["plugins"] == [{"runtime": "0.0.2"}]
    assert payload["lang"] == "python"
    await client.close()


@pytest.mark.asyncio
async def test_report_failed():
    """Test the report fails when the stat host rejects it"""
    client = Client(server=SERVER)
    with mock.patch.object(Client, "post", return_value=(500, "error")) as post:
        assert not await client.stats("0.1.11", [])
    assert post.call_count == 1


def test_handle_response():
    """Test the 403 response text handling"""
    client = Client(server=SERVER)
    assert client._handle_response(RESP_OK, "") == RESP_OK
    assert client._handle_response(RESP_FORBIDDEN, REPORT_REPEAT) == RESP_OK
    assert client._handle_response(RESP_FORBIDDEN, REPORT_LIMITED) == RESP_OK
    assert client._handle_response(RESP_FORBIDDEN, "other") == RESP_FORBIDDEN
    assert client._handle_response(500, REPORT_REPEAT) == 500


@mock.patch("trpc_metrics_runtime.stat.TrpcConfig", new_callable=FakeTrpcConfig)
def test_server_info_from_config(config_obj):
    """Fill server identity from global and server config.

    Args:
        config_obj: Fake tRPC config whose global IP and container are valid.
    """
    config_obj.global_config.local_ip = "1.2.3.4"
    config_obj.global_config.container_name = "container"
    config_obj.server.app = "app"
    config_obj.server.server = "server"
    client = Client()
    assert client.server_info == {"ip": "1.2.3.4", "container": "container", "app": "app", "server": "server"}


@mock.patch("trpc_metrics_runtime.stat.TrpcConfig", new_callable=FakeTrpcConfig)
@mock.patch("trpc_metrics_runtime.stat.get_default_ip", return_value="2.3.4.5")
@mock.patch("trpc_metrics_runtime.stat.get_default_container", return_value="a/b/c")
def test_server_info_without_global_config(get_default_container, get_default_ip, config_obj):
    """Fall back to the default IP and container when config is empty.

    Args:
        get_default_container: Patched container lookup.
        get_default_ip: Patched IP lookup.
        config_obj: Fake tRPC config that reports no global or server section.
    """
    config_obj.global_config.__bool__.return_value = False
    config_obj.server.__bool__.return_value = False
    client = Client()
    assert client.server_info == {"ip": "2.3.4.5", "container": "a/b/c"}
    get_default_ip.assert_called_once()
    get_default_container.assert_called_once()


@mock.patch("trpc_metrics_runtime.stat.TrpcConfig", new_callable=FakeTrpcConfig)
@mock.patch("trpc_metrics_runtime.stat.get_default_ip", return_value="3.4.5.6")
@mock.patch("trpc_metrics_runtime.stat.get_default_container", return_value="d/e/f")
def test_server_info_with_invalid_value(get_default_container, get_default_ip, config_obj):
    """Replace an unusable IP and an empty container with the defaults.

    Args:
        get_default_container: Patched container lookup.
        get_default_ip: Patched IP lookup.
        config_obj: Fake tRPC config with ``0.0.0.0`` and an empty container.
    """
    config_obj.global_config.local_ip = "0.0.0.0"
    config_obj.global_config.container_name = ""
    config_obj.server.__bool__.return_value = False
    client = Client()
    assert client.server_info == {"ip": "3.4.5.6", "container": "d/e/f"}
    get_default_ip.assert_called_once()
    get_default_container.assert_called_once()
