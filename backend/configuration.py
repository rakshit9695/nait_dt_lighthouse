"""Configuration loading + assumption tracking (spec §1.4, §2.3)."""
from __future__ import annotations

from functools import lru_cache
from pathlib import Path
from typing import Any

import yaml

from backend.contracts import AssumptionRef

ROOT = Path(__file__).resolve().parent.parent
CONFIG_DIR = ROOT / "backend" / "config"
ASSUMPTIONS_FILE = ROOT / "assumptions.md"


def _load_yaml(path: Path) -> dict[str, Any]:
    return yaml.safe_load(path.read_text(encoding="utf-8"))


@lru_cache(maxsize=1)
def load_defaults() -> dict[str, Any]:
    return _load_yaml(CONFIG_DIR / "defaults.yaml")["defaults"]


@lru_cache(maxsize=1)
def load_topology() -> dict[str, Any]:
    return _load_yaml(CONFIG_DIR / "topology.yaml")


@lru_cache(maxsize=1)
def load_weights() -> dict[str, float]:
    return _load_yaml(CONFIG_DIR / "weights.yaml")


def get(key: str) -> Any:
    return load_defaults()[key]["value"]


def assumptions_for(prefix: str) -> list[AssumptionRef]:
    out: list[AssumptionRef] = []
    for key, entry in load_defaults().items():
        if not key.startswith(prefix + "."):
            continue
        if entry.get("assumed", False):
            out.append(AssumptionRef(
                param=key,
                default_value=entry["value"],
                unit=entry.get("unit", ""),
                source_doc=entry.get("source", "Questions_for_NAIT.pdf"),
                question_index=int(entry.get("question_index", 0)),
                confidence_penalty=float(entry.get("confidence_penalty", 0.1)),
            ))
    return out


def all_assumptions() -> list[AssumptionRef]:
    out: list[AssumptionRef] = []
    for key, entry in load_defaults().items():
        if entry.get("assumed", False):
            out.append(AssumptionRef(
                param=key,
                default_value=entry["value"],
                unit=entry.get("unit", ""),
                source_doc=entry.get("source", "Questions_for_NAIT.pdf"),
                question_index=int(entry.get("question_index", 0)),
                confidence_penalty=float(entry.get("confidence_penalty", 0.1)),
            ))
    return out
