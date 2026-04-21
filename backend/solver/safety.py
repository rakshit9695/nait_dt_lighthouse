"""Safety envelope clipping (spec §3.5)."""
from __future__ import annotations

from typing import Any


def clip_command(component_id: str, command: dict[str, Any]) -> tuple[dict[str, Any], list[str]]:
    """Return (clipped_command, list_of_violation_keys)."""
    out = dict(command)
    violations: list[str] = []
    if component_id == "battery":
        if "SOC" in out:
            v = float(out["SOC"])
            if not (0.10 <= v <= 0.95):
                violations.append("battery.SOC")
            out["SOC"] = max(0.10, min(0.95, v))
        if "current_a" in out:
            v = float(out["current_a"])
            if abs(v) > 100.0:
                violations.append("battery.current_a")
            out["current_a"] = max(-100.0, min(100.0, v))
        if "T" in out and float(out["T"]) > 45.0:
            violations.append("battery.T_above_45C")
    if component_id == "quattro" and "power_w" in out:
        v = float(out["power_w"])
        if abs(v) > 5000.0:
            violations.append("quattro.power_w")
        out["power_w"] = max(-5000.0, min(5000.0, v))
    if component_id == "fronius" and "power_w" in out:
        v = float(out["power_w"])
        if v > 3800.0 or v < 0.0:
            violations.append("fronius.power_w")
        out["power_w"] = max(0.0, min(3800.0, v))
    if component_id == "grid" and "export_w" in out:
        v = float(out["export_w"])
        if v > 5000.0:
            violations.append("grid.export_w")
        out["export_w"] = min(5000.0, v)
    if component_id == "panel" and "branch_current_a" in out:
        v = float(out["branch_current_a"])
        if v > 30.0:
            violations.append("panel.branch_current_a")
        out["branch_current_a"] = min(30.0, v)
    return out, violations
