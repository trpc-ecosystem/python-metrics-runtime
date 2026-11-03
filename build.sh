#!/bin/bash
#
# Tencent is pleased to support the open source community by making tRPC-Metrics-Runtime available.
#
# Copyright (C) 2026 Tencent. All rights reserved.
#
# tRPC-Metrics-Runtime is licensed under Apache-2.0.

pip install --upgrade pip

pip3 uninstall -y trpc_metrics_runtime

pip3 install -r requirements.txt

pip install -e .
