# SPDX-License-Identifier: MIT
"""
Backward-compat alias: ``gh_install`` → ``pluck``.

This file lets ``from gh_install import ...`` and ``gh_install:main``
entry points keep working after the rename to ``pluck``.
"""

from pluck import *  # noqa: F401, F403
from pluck import main  # noqa: F401
