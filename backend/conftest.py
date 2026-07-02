"""确保测试可从 backend 目录导入 `app` 包。"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
