#!/bin/sh
#
# Tencent is pleased to support the open source community by making tRPC-Metrics-Runtime available.
#
# Copyright (C) 2026 Tencent. All rights reserved.
#
# tRPC-Metrics-Runtime is licensed under Apache-2.0.

sh +x build.sh

pip3 install -r requirements-test.txt

rm -rf coverage.xml
rm -rf test-ngtest-ut-trpc_metrics_runtime.xml
rm -rf .coverage
rm -rf htmlcov*


test_dir=trpc_metrics_runtime
pytest --cov-report html --cov-report term --cov-report xml --cov=$test_dir tests/  \
       --junitxml=test-ngtest-ut-$test_dir.xml > cov.tmp

