#!/usr/bin/env python3
"""
入金マッチング実行スクリプト
プロジェクトルートから実行することを想定
"""

import sys
from pathlib import Path

# プロジェクトルートをパスに追加
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from src.main_execution import main

if __name__ == "__main__":
    # 入金マッチングモードで実行
    sys.argv = [sys.argv[0], "--mode", "matching"]
    main() 