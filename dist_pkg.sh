#!/bin/sh
#
# Tencent is pleased to support the open source community by making tRPC-Metrics-Runtime available.
#
# Copyright (C) 2026 Tencent. All rights reserved.
#
# tRPC-Metrics-Runtime is licensed under Apache-2.0.

INIT_PY="trpc_metrics_runtime/version.py"

version=$(grep -oP "__version__ = '\K[^']+" "$INIT_PY")

echo "version is ${version}"

sh +x build.sh

sudo rm -rf dist/

pip3 install urllib3
pip install build
pip3 install twine
# dist source package
#python -m build --sdist
# dist wheel package
python -m build


twine upload dist/* -r tencent


