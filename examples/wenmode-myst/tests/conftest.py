from __future__ import annotations

import sys
from pathlib import Path

PACKAGE_ROOT = Path(__file__).resolve().parents[1]
REPO_ROOT = Path(__file__).resolve().parents[3]

sys.path.insert(0, str(REPO_ROOT / 'src'))
sys.path.insert(0, str(PACKAGE_ROOT / 'src'))
