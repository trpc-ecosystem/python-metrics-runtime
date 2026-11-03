# Tencent is pleased to support the open source community by making tRPC-Metrics-Runtime available.
#
# Copyright (C) 2026 Tencent. All rights reserved.
#
# tRPC-Metrics-Runtime is licensed under Apache-2.0.
"""HTTP client that posts framework and plugin versions to the stat service.

Each payload names the language, framework version, and the process identity
(``app``, ``server``, ``ip``, ``container``). The batch path also includes
every plugin that opted in. Reports are sent to ``stat.trpc.tencent.com``.
"""

from aiohttp import ClientSession

from trpc_sdk.config import TrpcConfig
from trpc_sdk.log import logger

from .constants import STAT_DOMAIN
from .constants import REPORT_LIMITED
from .constants import REPORT_REPEAT
from .constants import REQUEST_TIMEOUT
from .constants import RESP_FORBIDDEN
from .constants import RESP_OK
from .constants import STAT_URI
from .constants import STATS_URI
from .get_default_info import get_default_container
from .get_default_info import get_default_ip
from .utils import is_ip_valid


class Client:
    """POST version reports and treat duplicate or capped replies as success.

    The aiohttp session is created on first use and closed by ``close``.
    Server identity is filled from ``TrpcConfig`` and, when that is missing
    or not a usable address, from ``get_default_ip`` and ``get_default_container``.

    Attributes:
        headers: Extra HTTP headers sent with every report, or None.
        proxy: Proxy URL passed to aiohttp, or None.
        _loop: Event loop bound to the session. None uses aiohttp's default.
        _session: Open ``ClientSession``, or None before the first request and after ``close``.
        _timeout: Request timeout in seconds accepted at construction.
        _server_info: Cached ``app``, ``server``, ``ip``, and ``container`` fields.
    """

    def __init__(self, loop=None, timeout: int = REQUEST_TIMEOUT, headers: dict = None, proxy: str = None, **kwargs):
        """Store connection options and any caller-supplied server identity.

        Args:
            loop: Event loop for the aiohttp session.
            timeout: Request timeout in seconds.
            headers: Extra HTTP headers, or None.
            proxy: Proxy URL, or None.
            **kwargs: Optional ``server`` mapping copied into ``_server_info``.
        """
        self._loop = loop
        self._session = None
        self._timeout = timeout
        self.headers = headers
        self.proxy = proxy
        self._server_info = dict(kwargs).get("server", None) or {}

    @property
    def server_info(self):
        """Return process identity fields, filling any that are still missing.

        The cache is filled when it is empty or contains none of ``app``,
        ``server``, ``ip``, and ``container``. A mapping that already has any of
        those keys is returned unchanged. While filling, values come from
        ``TrpcConfig``. An invalid or absent IP is replaced by ``get_default_ip``,
        and an empty container name by ``get_default_container``.

        Returns:
            Mapping with ``app``, ``server``, ``ip``, and ``container``.
        """
        if not self._server_info or self._server_info.keys().isdisjoint(["app", "server", "ip", "container"]):
            server = TrpcConfig.server_config()
            if server:
                self._server_info.update(dict(app=server.app, server=server.server))

            global_config = TrpcConfig.global_config()
            if global_config:
                self._server_info.update(dict(container=global_config.container_name, ip=global_config.local_ip))

            # Config may omit the address or publish 0.0.0.0. Replace those before sending.
            if "ip" not in self._server_info or not is_ip_valid(self._server_info["ip"]):
                self._server_info["ip"] = get_default_ip()
            if "container" not in self._server_info or len(self._server_info["container"]) == 0:
                self._server_info["container"] = get_default_container()

        return self._server_info

    @property
    def session(self):
        """Return the aiohttp session, creating it on first use.

        Returns:
            The process-lifetime ``ClientSession`` for this client.
        """
        if not self._session:
            self._session = ClientSession(loop=self._loop)

        return self._session

    async def close(self):
        """Close the aiohttp session and drop the reference.

        A later request creates a new session. Safe to call when no session
        has been opened yet.
        """
        if self._session:
            await self._session.close()

        self._session = None

    def _url(self, uri):
        """Build an HTTP URL for a stat path on the public host.

        Args:
            uri: Path such as ``STATS_URI``, without a leading slash.

        Returns:
            Absolute ``http://`` URL for ``stat.trpc.tencent.com``.
        """
        return f"http://{STAT_DOMAIN}/{uri}"

    def _generate_request_payload(self, version):
        """Build the common JSON body shared by the batch and legacy paths.

        Args:
            version: tRPC framework version, not this package's ``__version__``.

        Returns:
            Mapping with ``lang``, ``version``, and the ``server_info`` fields.
        """
        payload = {
            "lang": "python",
            "version": version,
        }

        # app, server, container, and ip identify which process is reporting.
        payload.update(self.server_info)

        return payload

    async def stats(self, version: str, plugins: list):
        """Report the framework version and every opted-in plugin in one request.

        This is the v3 batch path used by the daily loop. ``plugins`` is a list
        of single-key mappings such as ``{"m007": "1.2.0"}``.

        Args:
            version: tRPC framework version.
            plugins: Plugin name-to-version mappings. None is sent as an empty list.

        Returns:
            True when the stat service accepts the report, including a duplicate
            or over-limit reply treated as success.
        """
        payload = self._generate_request_payload(version)

        # One payload carries the whole plugin set so the service can cap per day.
        payload.update({"plugins": plugins or []})

        return await self._report(STATS_URI, payload)

    async def stat(self, plugin: str, version: str = ""):
        """Report a single plugin on the legacy path.

        Deprecated: callers should use ``stats``, which sends the framework
        version and all plugins together. This method remains so older plugins
        can still post one name.

        Args:
            plugin: Plugin name. None or an empty value is sent as ``""``.
            version: Framework version placed in the common payload fields.

        Returns:
            True when the stat service accepts the report, including a duplicate
            or over-limit reply treated as success.
        """
        payload = self._generate_request_payload(version)

        # Legacy body uses a single name, not the v3 plugins list.
        payload.update({"plugin": plugin or ""})

        return await self._report(STAT_URI, payload)

    async def _report(self, uri, payload):
        """POST ``payload`` to the public stat host.

        A non-success status is logged. Transport errors propagate to the caller.

        Args:
            uri: Stat path, either ``STATS_URI`` or ``STAT_URI``.
            payload: JSON body from ``_generate_request_payload``.

        Returns:
            True when the host accepts the report.
        """
        url = self._url(uri)
        status, text = await self.post(url, payload, self.headers, self.proxy)
        if status != RESP_OK:
            logger.warning("fail to request stat url %s has resp %d %s ", url, status, text)

        return status == RESP_OK

    def _handle_response(self, status, resp):
        """Map a duplicate or over-limit 403 onto the success status.

        Any status other than 403 is returned unchanged. A 403 whose body
        contains the already-reported or daily-limit text is treated as
        success so the daily loop does not retry a report the service already
        counted. Other 403 bodies stay failures.

        Args:
            status: HTTP status from aiohttp.
            resp: Response body text.

        Returns:
            ``RESP_OK`` for an accepted, duplicate, or capped report; otherwise
            the original status.
        """
        if status != RESP_FORBIDDEN:
            return status

        # The service already stored today's report for this process.
        if REPORT_REPEAT in resp:
            return RESP_OK

        # The per-service, per-container daily cap was already reached.
        if REPORT_LIMITED in resp:
            return RESP_OK

        return status

    async def post(self, url, payload: dict, headers: dict = None, proxy: str = None):
        """POST ``payload`` as JSON and normalize the stat-service status.

        Args:
            url: Absolute report URL.
            payload: JSON object.
            headers: Extra HTTP headers, or None.
            proxy: Proxy URL, or None.

        Returns:
            Pair of normalized status and raw response text.
        """
        async with self.session.post(url, json=payload, headers=headers, proxy=proxy) as resp:
            status = resp.status
            text = await resp.text()

            status = self._handle_response(status, text)

            logger.debug(f"{url} {payload} {status} {text}")

            return status, text
