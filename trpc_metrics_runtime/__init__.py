# Tencent is pleased to support the open source community by making tRPC-Metrics-Runtime available.
#
# Copyright (C) 2026 Tencent. All rights reserved.
#
# tRPC-Metrics-Runtime is licensed under Apache-2.0.
"""Daily usage reporter for the tRPC Python framework and its plugins.

Importing this package registers ``RuntimeMetrics``. On worker start the
plugin starts one daemon thread that reports the framework version and every
plugin marked ``report=True``, then repeats that report every 24 hours.

Public API:

    RuntimeMetrics: Metrics plugin that starts the shared reporter.
    instance: Return the registered ``RuntimeMetrics`` plugin.
    ReportClient: HTTP client that posts version payloads to the stat service.
    daily_report: Async loop that waits, reports, and sleeps until the next day.
    async_sleep: ``asyncio.sleep`` wrapper that still accepts ``loop`` before 3.10.
    get_default_ip: Fallback address when server config has no usable IP.
    get_default_container: Fallback container id from pod env or host IP.
    is_ip_valid: Whether an address is a reportable public or overlay IP.
    is_in_docker: Whether this process appears to run inside Docker.
    __version__: Version of this reporter package, distinct from the framework.
"""

from .get_default_info import get_default_ip
from .get_default_info import get_default_container
from .plugin import instance
from .plugin import RuntimeMetrics
from .runtime import async_sleep
from .runtime import daily_report
from .stat import Client as ReportClient
from .utils import is_ip_valid
from .utils import is_in_docker

__all__ = [
    "RuntimeMetrics",
    "instance",
    "ReportClient",
    "daily_report",
    "async_sleep",
    "get_default_ip",
    "get_default_container",
    "is_ip_valid",
    "is_in_docker",
]
