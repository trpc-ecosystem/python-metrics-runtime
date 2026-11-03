# Tencent is pleased to support the open source community by making tRPC-Metrics-Runtime available.
#
# Copyright (C) 2026 Tencent. All rights reserved.
#
# tRPC-Metrics-Runtime is licensed under Apache-2.0.
"""Constants for the runtime version reporter.

Intervals, HTTP status handling, the stat-service host, and request paths live
here so the report loop and the HTTP client share one definition.
"""

import sys

# True on Python 3.10+, where asyncio.sleep no longer accepts a loop argument.
PY_310 = sys.version_info >= (3, 10)

# Name used when this package registers itself as a metrics plugin.
PLUGIN_NAME = "runtime"
# Thread name of the daemon that runs the daily report loop.
REPORTER_NAME = "runtime-metrics-reporter"

# Seconds between successful or failed report attempts. One calendar day.
REPORT_INTERVAL = 24 * 60 * 60
# Seconds to wait after process start before the first report, so plugins finish init.
INIT_DELAY = 3

# HTTP status the stat service returns for an accepted report.
RESP_OK = 200
# HTTP status the stat service returns when a report is duplicate or over the daily cap.
RESP_FORBIDDEN = 403
# Seconds before an aiohttp report request is abandoned.
REQUEST_TIMEOUT = 30

# Substring of a 403 body meaning this service already reported today.
REPORT_REPEAT = "已上报"
# Substring of a 403 body meaning this service exceeded the per-container daily cap.
REPORT_LIMITED = "上报次数限制"

# Public host that receives framework and plugin version reports.
STAT_DOMAIN = "stat.trpc.tencent.com"

# Path that submits framework version and every plugin version in one payload.
STATS_URI = "api/trpc/stat/v3/add"
# Legacy path that submits a single plugin name. Kept for older callers.
STAT_URI = "api/trpc/stat/add"
