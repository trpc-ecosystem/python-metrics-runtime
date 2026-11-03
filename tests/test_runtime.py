# Tencent is pleased to support the open source community by making tRPC-Metrics-Runtime available.
#
# Copyright (C) 2026 Tencent. All rights reserved.
#
# tRPC-Metrics-Runtime is licensed under Apache-2.0.
""" Test runtime"""
import asyncio
from unittest import mock

import pytest

from trpc_metrics_runtime.constants import PY_310
from trpc_metrics_runtime.runtime import async_sleep
from trpc_metrics_runtime.runtime import daily_report
from trpc_metrics_runtime.stat import Client
from trpc_metrics_runtime.version import __version__
from .utils import DUMMY_PLUGIN_SPECS


@pytest.mark.asyncio
async def test_daily_reporter():
    """Test daily reporter reports only the plugins marked report on every interval"""
    with mock.patch.object(Client, "stats", return_value=True) as stats:
        task = asyncio.ensure_future(
            daily_report(asyncio.get_running_loop(), delay=0, interval=0.05, plugin_specs=DUMMY_PLUGIN_SPECS))
        await asyncio.sleep(0.2)
        task.cancel()
        with pytest.raises(asyncio.CancelledError):
            await task

    assert stats.call_count >= 2
    assert stats.call_args.args[1] == [{"runtime": "0.0.2"}]


@pytest.mark.asyncio
async def test_daily_reporter_default_specs():
    """Test daily reporter reads the plugin manager by default"""
    with mock.patch.object(Client, "stats", return_value=True) as stats:
        task = asyncio.ensure_future(daily_report(delay=0, interval=0.05))
        await asyncio.sleep(0.1)
        task.cancel()
        with pytest.raises(asyncio.CancelledError):
            await task

    assert {"runtime": __version__} in stats.call_args.args[1]


@pytest.mark.asyncio
async def test_daily_reporter_recovers_from_error():
    """Test daily reporter keeps running after a report error"""
    with mock.patch.object(Client, "stats", side_effect=[RuntimeError("boom"), True, True]) as stats:
        task = asyncio.ensure_future(daily_report(delay=0, interval=0.05, plugin_specs=DUMMY_PLUGIN_SPECS))
        await asyncio.sleep(0.2)
        task.cancel()
        with pytest.raises(asyncio.CancelledError):
            await task

    assert stats.call_count >= 2


@pytest.mark.asyncio
async def test_async_sleep():
    """Test async sleep"""
    await async_sleep(0.01, True)
    await async_sleep(0.01, PY_310, asyncio.get_running_loop())
