#!/bin/bash
#
# Tencent is pleased to support the open source community by making tRPC-Metrics-Runtime available.
#
# Copyright (C) 2026 Tencent. All rights reserved.
#
# tRPC-Metrics-Runtime is licensed under Apache-2.0.

sudo rm  -rf  coverage.xml
sudo rm  -rf  *.log
sudo rm  -rf  htmlcov
sudo rm  -rf  .coverage
sudo rm  -rf  .__*
sudo rm  -rf  trpc_metrics_runtime.egg-info
sudo rm  -rf dist/
sudo rm  -rf build/


sudo rm  -rf  test_tracemalloc*
sudo rm  -rf  test-ngtest-ut-trpc_metrics_runtime*
sudo rm  -rf  cov.tmp


find -type d | grep __pycache__ | xargs sudo rm  -r

find ./ -type f -name "*.log" -exec sudo rm {} \;