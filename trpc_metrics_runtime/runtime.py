# Tencent is pleased to support the open source community by making tRPC-Metrics-Runtime available.
#
# Copyright (C) 2026 Tencent. All rights reserved.
#
# tRPC-Metrics-Runtime is licensed under Apache-2.0.
"""Daily loop that reports the framework version and opted-in plugins.

The first report waits ``INIT_DELAY`` so plugin registration can finish.
Later reports wait ``REPORT_INTERVAL``. A failed request closes the HTTP
client and opens a new one before the next sleep.
"""

import asyncio

from trpc_sdk.log import logger
from trpc_sdk.plugin import DEFAULT_PLUGIN_MANAGER
from trpc_sdk.version import __version__ as trpc_version

from .constants import INIT_DELAY
from .constants import PY_310
from .constants import REPORT_INTERVAL
from .stat import Client


async def async_sleep(delay: int, is_py10: bool, loop=None):
    """Sleep without passing ``loop`` on Python 3.10 and newer.

    ``asyncio.sleep`` dropped the ``loop`` keyword in 3.10. Older interpreters
    still need it when the report task runs on a loop that is not the running
    loop.

    Args:
        delay: Seconds to sleep.
        is_py10: True when ``asyncio.sleep`` must be called without ``loop``.
        loop: Event loop forwarded only when ``is_py10`` is False.

    Returns:
        None. The coroutine finishes after ``delay`` seconds.
    """
    if is_py10:
        await asyncio.sleep(delay)
    else:
        await asyncio.sleep(delay, loop=loop)


async def daily_report(loop=None, delay=INIT_DELAY, interval=REPORT_INTERVAL, proxy=None, plugin_specs=None):
    """Report framework and plugin versions, then repeat on a fixed interval.

    The coroutine waits ``delay`` once, then loops forever. Each pass collects
    plugin specs whose ``report`` flag is set, posts them with
    ``Client.stats``, and sleeps ``interval`` seconds. When the post raises,
    the client is closed and replaced so the next pass does not reuse a broken
    session. A false return from ``stats`` is logged and does not rebuild the
    client.

    Args:
        loop: Event loop stored on the report client and forwarded to ``async_sleep``.
        delay: Seconds to wait before the first report.
        interval: Seconds between reports. The default is 24 hours.
        proxy: Proxy URL passed to the report client, or None.
        plugin_specs: Specs to report. None reads ``DEFAULT_PLUGIN_MANAGER``.

    Returns:
        None. The coroutine does not finish on its own.
    """

    # Let plugin registration finish before the first snapshot is taken.
    await async_sleep(delay, PY_310, loop)

    reporter = Client(loop=loop, proxy=proxy)

    # One pass per interval for the life of the reporter thread.
    while True:
        # Tests inject specs; production reads whatever is registered now.
        specs = plugin_specs or DEFAULT_PLUGIN_MANAGER.all_plugin_specs()

        # The stat service caps reports, so plugins that did not opt in are omitted.
        plugins = [{s.plugin_name: s.version} for s in specs if s.report]

        # Framework version and the opted-in plugin map go out as one v3 payload.
        try:
            ret = await reporter.stats(trpc_version, plugins)
            if not ret:
                logger.info(f"fail to report trpc version {trpc_version} and plugins {plugins} error")
        except Exception as e:  # pylint: disable=broad-except
            logger.info(f"fail to report trpc version {trpc_version} and plugins {plugins} error: {e}")
            await reporter.close()
            reporter = Client(loop=loop, proxy=proxy)

        # Interval is measured from the end of the attempt, not from process start.
        await async_sleep(interval, PY_310, loop)
