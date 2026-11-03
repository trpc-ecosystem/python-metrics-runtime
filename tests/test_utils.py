# Tencent is pleased to support the open source community by making tRPC-Metrics-Runtime available.
#
# Copyright (C) 2026 Tencent. All rights reserved.
#
# tRPC-Metrics-Runtime is licensed under Apache-2.0.
""" Test utils functions."""

from trpc_metrics_runtime.utils import is_ip_valid


def test_check_ip_valid():
    """ Test check ip valid."""
    test_case = [
        {
            "ip": "",
            "want": False
        },
        {
            "ip": "???",
            "want": False
        },
        {
            "ip": "0.0.0.0",
            "want": False
        },
        {
            "ip": "::",
            "want": False
        },
        {
            "ip": "127.0.0.1",
            "want": False
        },
        {
            "ip": "127.0.0.255",
            "want": False
        },
        {
            "ip": "::1",
            "want": False
        },
        {
            "ip": "169.254.1.1",
            "want": False
        },
        {
            "ip": "fe80::42:c0ff:fea8:a02",
            "want": False
        },
        {
            "ip": "172.16.0.1",
            "want": False
        },
        {
            "ip": "192.168.10.6",
            "want": False
        },
        {
            "ip": "FEC0::1:2:3:4",
            "want": False
        },
        {
            "ip": "fd12:3456:789a:1::1",
            "want": False
        },
        {
            "ip": "1.2.3.4",
            "want": True
        },
        {
            "ip": "2402:4e00::",
            "want": True
        },
    ]
    for c in test_case:
        assert is_ip_valid(c["ip"]) == c["want"]
