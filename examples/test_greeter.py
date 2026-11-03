# Tencent is pleased to support the open source community by making tRPC-Metrics-Runtime available.
#
# Copyright (C) 2026 Tencent. All rights reserved.
#
# tRPC-Metrics-Runtime is licensed under Apache-2.0.
"""Entry point that runs the example Greeter client.

Kept so older tests can still launch the client through this module.
"""

import os
import sys

sys.path.append(os.path.abspath(os.path.dirname(__file__)))

from test_service_rpc import main as test_run

# Compatibility shim for older tests. The client lives in ``test_run``.
if __name__ == "__main__":
    sys.exit(test_run())
