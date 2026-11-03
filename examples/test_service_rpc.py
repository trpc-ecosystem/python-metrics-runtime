# Tencent is pleased to support the open source community by making tRPC-Metrics-Runtime available.
#
# Copyright (C) 2026 Tencent. All rights reserved.
#
# tRPC-Metrics-Runtime is licensed under Apache-2.0.
"""Example client that calls Greeter.SayHello through the tRPC stub.

By default the process sends one synchronous call and exits. ``--loop`` keeps
sending the async call until the process is interrupted.
"""

import argparse
import os
import sys
import asyncio

from trpc_sdk.abc import TrpcContext
from trpc_sdk.client import Options
from trpc_sdk.config import TrpcConfig
from trpc_sdk.log import logger
from trpc_sdk.plugin import init_plugins
from trpc_sdk.serialization import SerializationType

# add the stub to the path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "stub")))  # noqa
sys.path.append(os.path.abspath(os.path.dirname(__file__)))  # noqa

# DO NOT remove the plugin below!
import trpc_metrics_runtime as _

from trpc_trpc_python_group_helloworld import pb
from trpc_trpc_python_group_helloworld import rpc


# pylint: disable=invalid-name
def test_sync_Greeter_SayHello():
    """Test Greeter of SayHello"""
    proxy = rpc.GreeterClientProxyImpl()
    req = pb.HelloRequest()
    req.msg = 'hello'
    options = (Options().set_target('ip://127.0.0.1:8000').set_protocol('trpc').set_serialization_type(
        SerializationType.PB).set_network('tcp'))
    ctx = TrpcContext()
    try:
        ret = proxy.SayHello(ctx, req, options)
        print(f"\n  test_sync_Greeter_SayHello recv result is {ret}\n")
        assert ret is not None
    except Exception as exc:  # pylint: disable=broad-except
        logger.error(exc)
        assert 0


# pylint: disable=invalid-name
async def test_Greeter_SayHello():
    """Async test Greeter of SayHello"""
    proxy = rpc.GreeterClientProxyImpl()
    req = pb.HelloRequest()
    req.msg = 'hello'
    options = (Options().set_target('ip://127.0.0.1:8000').set_protocol('trpc').set_serialization_type(
        SerializationType.PB).set_network('tcp').set_namespace('Development').set_timeout(3000))
    ctx = TrpcContext()
    while True:
        try:
            ret = await proxy.asyncSayHello(ctx, req, options)
            print(f"\n  test_Greeter_SayHello recv result is {ret}\n")
            assert ret is not None
        except Exception as exc:  # pylint: disable=broad-except
            logger.error(f"test_Greeter_SayHello error: {exc}")
            assert 0
        await asyncio.sleep(100)


def main() -> int:
    """Load the example config, initialize plugins, and call SayHello.

    The default path sends one synchronous SayHello and returns. ``--loop``
    keeps sending the async call until the process is interrupted.

    A config file is optional. When several sources set the same field, an
    explicit client option wins, then the config file, then the framework
    default.

    Returns:
        ``0`` when the one-shot call succeeds, ``1`` when it fails.
    """
    parser = argparse.ArgumentParser(description="Example Greeter client")
    parser.add_argument("--loop", action="store_true", help="Keep calling SayHello until interrupted.")
    args = parser.parse_args()
    # A config file is optional. An explicit client option wins, then the
    # config file, then the framework default.
    config_path = os.path.abspath(os.path.join(os.path.dirname(__file__), "trpc_python.yaml"))
    TrpcConfig.load(config_path, 'utf-8')
    init_plugins()
    if args.loop:
        asyncio.run(test_Greeter_SayHello())
        return 0
    try:
        test_sync_Greeter_SayHello()
    except Exception:  # pylint: disable=broad-except
        return 1
    return 0


if __name__ == "__main__":
    # A config file is optional. An explicit client option wins, then the
    # config file, then the framework default.
    sys.exit(main())
