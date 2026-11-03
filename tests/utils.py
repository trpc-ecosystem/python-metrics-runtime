# Tencent is pleased to support the open source community by making tRPC-Metrics-Runtime available.
#
# Copyright (C) 2026 Tencent. All rights reserved.
#
# tRPC-Metrics-Runtime is licensed under Apache-2.0.
"""Shared fixtures for the runtime metrics tests."""
from types import SimpleNamespace
from unittest import mock

SERVER = {"app": "trpc_demo", "server": "test_server", "container": "local", "ip": "127.0.0.1"}

DUMMY_PLUGIN_SPECS = [
    SimpleNamespace(plugin_name="runtime", version="0.0.2", report=True),
    SimpleNamespace(plugin_name="test", version="0.0.2", report=False),
]


class FakeTrpcConfig(mock.MagicMock):
    """Stand-in whose config methods return the attributes of the same name.

    ``global_config()`` returns ``global_config`` and ``server_config()``
    returns ``server``, so tests can set fields on those attributes.
    """

    def __init__(self, *args, **kwargs):
        """Wire the config methods to return this mock's own attributes.

        Args:
            *args: Positional arguments forwarded to ``MagicMock``.
            **kwargs: Keyword arguments forwarded to ``MagicMock``.
        """
        super().__init__(*args, **kwargs)
        self.global_config.side_effect = lambda: self.global_config
        self.server_config.side_effect = lambda: self.server

    def _get_child_mock(self, **kwargs):
        """Build child mocks as plain ``MagicMock`` instances.

        The base class would otherwise nest another ``FakeTrpcConfig``, which
        re-enters this constructor.

        Args:
            **kwargs: Attributes applied to the child mock.

        Returns:
            A ``MagicMock`` configured with ``kwargs``.
        """
        return mock.MagicMock(**kwargs)
