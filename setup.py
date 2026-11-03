# Tencent is pleased to support the open source community by making tRPC-Metrics-Runtime available.
#
# Copyright (C) 2026 Tencent. All rights reserved.
#
# tRPC-Metrics-Runtime is licensed under Apache-2.0.
"""Install entry point for the trpc-metrics-runtime package."""

import codecs
import os
import re
from setuptools import find_packages
from setuptools import setup


def _read_version():
    """Read ``__version__`` from the package version module.

    Returns:
        The semantic version string declared in ``version.py``.

    Raises:
        RuntimeError: The version assignment is missing.
    """
    regexp = re.compile(r"^__version__\W*=\W*'(\d\.\d\.\d(-(alpha|beta|rc)\.\d)?)'")
    init_py = os.path.join(os.path.dirname(__file__), "trpc_metrics_runtime", "version.py")
    with open(init_py, encoding="utf-8") as f:
        for line in f:
            match = regexp.match(line)
            if match is not None:
                return match.group(1)
        raise RuntimeError(f"Cannot find version in {init_py}")


setup(
    name="trpc-metrics-runtime",
    version=_read_version(),
    packages=find_packages(exclude=["tests"]),
    maintainer="tRPC Group",
    description="runtime metrics plugin for trpc framework",
    long_description=codecs.open('README.md', encoding='UTF-8').read(),
    long_description_content_type="text/markdown",
    url="",
    project_urls={
        "Documentation": "",
        "Code": "",
        "Issue tracker": "",
    },
    python_requires=">=3.8",
    install_requires=[
        "trpc-python ; sys_platform != 'win32'",
        "aiohttp>=3.6.2",
        "netifaces",
    ],
    package_data={},
    include_package_data=True,  # Include files listed in MANIFEST.in.
    exclude_package_data={'': ['.gitignore']},
    scripts=[],
    cmdclass={},
    entry_points={})
