# Tencent is pleased to support the open source community by making tRPC-Metrics-Runtime available.
#
# Copyright (C) 2026 Tencent. All rights reserved.
#
# tRPC-Metrics-Runtime is licensed under Apache-2.0.
"""Metrics plugin that starts the daily version reporter exactly once.

Worker processes share one ``multiprocessing.Value`` flag. The first worker
to pass the lock starts a daemon thread; later workers return immediately.
The thread owns an event loop and runs ``daily_report`` until the process exits.
"""

import asyncio
import os
import threading
import multiprocessing
from multiprocessing import Value

from trpc_sdk.abc import BasePlugin
from trpc_sdk.abc import PluginInitPos
from trpc_sdk.abc import PluginType
from trpc_sdk.config import TrpcConfig
from trpc_sdk.log import logger
from trpc_sdk.plugin import get_plugin
from trpc_sdk.plugin import register_plugin
from trpc_sdk.utils import get_async_lib
from trpc_sdk.version import __version__ as trpc_version

from .constants import PLUGIN_NAME
from .constants import REPORTER_NAME
from .runtime import daily_report
from .version import __version__ as version


def instance():
    """Return the registered runtime metrics plugin.

    Returns:
        The plugin object stored under ``PluginType.METRICS`` and ``PLUGIN_NAME``.
    """
    return get_plugin(PluginType.METRICS, PLUGIN_NAME)


class _ReporterMetrics:
    """Daemon thread that runs the daily report coroutine.

    Construction starts the thread. The thread is a daemon so process exit
    does not wait for the next 24-hour sleep.

    Attributes:
        name: Thread name, ``REPORTER_NAME``.
        _thread: Running reporter thread, or None before ``_run``.
    """

    def __init__(self):
        """Name the reporter and start its daemon thread."""
        self.name = REPORTER_NAME
        self._thread = None
        self._run()

    def _reporter(self):
        """Run ``daily_report`` on a private event loop until it raises.

        The loop comes from ``get_async_lib`` at call time, so it follows
        ``global.enable_uvloop``, and is installed as this thread's current
        loop. A failure is logged with the framework version and does not
        get restarted here; the process must start a new reporter to try again.
        """
        loop = get_async_lib(TrpcConfig.global_config().enable_uvloop).new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            loop.run_until_complete(daily_report(loop))
        except Exception as e:  # pylint: disable=broad-except
            logger.info(f"fail to report trpc version {trpc_version} error: {e}")

    def _run(self):
        """Start the daemon thread once for this object.

        A second call returns without creating another thread.
        """
        if self._thread is not None:
            return
        self._thread = threading.Thread(name=self.name, target=self._reporter)
        self._thread.daemon = True
        self._thread.start()


# Shared across forked workers. The first worker to set it owns the reporter.
_shared_reporter = Value('b', False)


@register_plugin(PluginType.METRICS, PLUGIN_NAME, init_pos=PluginInitPos.WORKER, version=version, report=True)
class RuntimeMetrics(BasePlugin):
    """Worker plugin that publishes framework and plugin versions.

    ``init_pos`` is ``WORKER``, so each worker calls ``start``. The shared
    flag makes only one of those calls launch ``_ReporterMetrics``. This
    plugin itself is registered with ``report=True``, so its package version
    is included in the payload.
    """

    def start(self):
        """Start the shared reporter if no worker has started it yet."""
        self._run()

    def _run(self):
        """Claim the shared flag, then attach one reporter to this process.

        The check and the store run under the value's lock so two workers
        cannot both observe false. The reporter object is created after the
        lock is released and stored on the current process as ``reporter``
        so the thread is not collected while the worker stays alive.
        """
        # The lock covers the read and the write, not reporter construction.
        with _shared_reporter.get_lock():
            if _shared_reporter.value:
                return
            _shared_reporter.value = True
        logger.info("runtime metrics reporter started in pid %s", os.getpid())
        reporter = _ReporterMetrics()
        obj = multiprocessing.current_process()
        setattr(obj, "reporter", reporter)
