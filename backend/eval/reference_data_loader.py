"""Reference dataset loader (spec §4.1).

We can't redistribute proprietary datasets in this repo. The manifest documents
canonical sources + SHAs, and synthetic curves are bundled so empirical_match
scores are computable out of the box.
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parent.parent.parent
REF_DIR = ROOT / "backend" / "reference_data"


REFERENCE_TARGETS: dict[str, dict[str, Any]] = {
    # observed_field -> reference value at nominal operating point
    "pv_sim": {"P_dc": 12000.0, "tolerance": 3000.0},
    "fronius": {"efficiency": 0.966, "tolerance": 0.04},
    "battery": {"SOH": 1.0, "tolerance": 0.10},
    "quattro": {"V_ac_out": 120.0, "tolerance": 6.0},
    "generator": {"V_dc": 48.0, "tolerance": 8.0},
    "data_center": {"PUE": 1.6, "tolerance": 0.2},
    "grid": {"V": 240.0, "tolerance": 12.0},
    "panel": {"voltage_v": 240.0, "tolerance": 24.0},
    "dcdc": {"efficiency": 0.94, "tolerance": 0.10},
    "mts": {"transfer_time_s": 0.1, "tolerance": 0.2},
    "chroma": {"V": 240.0, "tolerance": 30.0},
    "cerbo": {"minimum_soc": 0.20, "tolerance": 0.10},
    "plc": {"loop_rate_hz": 1.0, "tolerance": 0.5},
}


def load_manifest() -> dict[str, Any]:
    p = REF_DIR / "manifest.json"
    if p.exists():
        return json.loads(p.read_text(encoding="utf-8"))
    return {"datasets": []}
