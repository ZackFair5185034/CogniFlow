# -*- coding: utf-8 -*-
"""
CogniFlow root conftest.py
让 backend.tests.* 能 import backend.services.* 等模块
"""
import sys
from pathlib import Path

# 把 backend/ 目录加到 sys.path, 让 backend.services/... 等可直接 import
_backend = Path(__file__).parent / "backend"
if str(_backend) not in sys.path:
    sys.path.insert(0, str(_backend))
