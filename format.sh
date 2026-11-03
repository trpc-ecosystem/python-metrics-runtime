#!/bin/sh
#
# Tencent is pleased to support the open source community by making tRPC-Metrics-Runtime available.
#
# Copyright (C) 2026 Tencent. All rights reserved.
#
# tRPC-Metrics-Runtime is licensed under Apache-2.0.

python3 -m pip install --upgrade pip 

pip3 install yapf


# 查找并格式化 Python 文件
find . -name "*.py" -not -path "./venv/*" \
                    -not -name "helloworld_pb2.py"  \
                    -exec yapf -i {} \;



