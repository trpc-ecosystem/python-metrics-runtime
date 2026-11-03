# Tencent is pleased to support the open source community by making tRPC-Metrics-Runtime available.
#
# Copyright (C) 2026 Tencent. All rights reserved.
#
# tRPC-Metrics-Runtime is licensed under Apache-2.0.
""" Test plugin"""
import multiprocessing
from unittest import mock

from trpc_sdk.abc import BasePlugin
from trpc_sdk.abc import PluginInitPos
from trpc_sdk.abc import PluginType
from trpc_sdk.plugin import DEFAULT_PLUGIN_MANAGER
from trpc_sdk.plugin import init_task_plugins
from trpc_sdk.plugin import init_worker_plugins
from trpc_metrics_runtime import plugin as plugin_module
from trpc_metrics_runtime.constants import PLUGIN_NAME
from trpc_metrics_runtime.plugin import RuntimeMetrics
from trpc_metrics_runtime.plugin import instance
from trpc_metrics_runtime.version import __version__


def _runtime_spec():
    """Return the registered spec of this plugin."""
    return DEFAULT_PLUGIN_MANAGER.get_plugin_spec(PluginType.METRICS, PLUGIN_NAME)


def test_plugin_object():
    """Test plugin object"""
    plugin = RuntimeMetrics()
    assert isinstance(plugin, BasePlugin)


def test_plugin_marked_report():
    """Test the plugin is registered with the report flag"""
    spec = _runtime_spec()
    assert spec.report
    assert spec.version == __version__


@mock.patch.object(plugin_module, "_ReporterMetrics")
def test_plugin_instance_starts_reporter_once(reporter_cls):
    """Test the reporter starts once however many times the plugin starts"""
    with mock.patch.object(plugin_module, "_shared_reporter", plugin_module.Value('b', False)):
        plugin = instance()
        assert isinstance(plugin, RuntimeMetrics)
        assert plugin.name == PLUGIN_NAME
        assert plugin.init_pos == PluginInitPos.WORKER

        plugin.start()
        RuntimeMetrics().start()

    reporter_cls.assert_called_once()


def test_forked_workers_start_one_reporter():
    """Test forked workers (rpc tasks, multi-process merge workers) start one reporter between them"""
    ctx = multiprocessing.get_context("fork")
    started = ctx.Value('i', 0)

    def fake_reporter():
        with started.get_lock():
            started.value += 1

    with mock.patch.object(plugin_module, "_shared_reporter", ctx.Value('b', False)), \
            mock.patch.object(plugin_module, "_ReporterMetrics", fake_reporter):
        workers = [ctx.Process(target=lambda: RuntimeMetrics().start()) for _ in range(4)]
        for worker in workers:
            worker.start()
        for worker in workers:
            worker.join(10)

    assert [worker.exitcode for worker in workers] == [0, 0, 0, 0]
    assert started.value == 1


@mock.patch.object(plugin_module, "_ReporterMetrics")
def test_task_plugins_do_not_start_reporter(reporter_cls):
    """Test the TASK pass (separate I/O process, task processes) skips this plugin"""
    with mock.patch.object(plugin_module, "_shared_reporter", plugin_module.Value('b', False)), \
            mock.patch.object(DEFAULT_PLUGIN_MANAGER, "all_plugin_specs", return_value=[_runtime_spec()]):
        init_task_plugins()

    reporter_cls.assert_not_called()


@mock.patch.object(plugin_module, "_ReporterMetrics")
def test_worker_plugins_start_reporter(reporter_cls):
    """Test the WORKER pass (merge, rpc task, multi-process merge) starts the reporter once"""
    with mock.patch.object(plugin_module, "_shared_reporter", plugin_module.Value('b', False)), \
            mock.patch.object(DEFAULT_PLUGIN_MANAGER, "all_plugin_specs", return_value=[_runtime_spec()]):
        init_worker_plugins()
        init_worker_plugins()

    reporter_cls.assert_called_once()
