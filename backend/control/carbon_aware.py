"""Carbon-aware controller (spec §2.2.13.3)."""
from __future__ import annotations

from typing import Any


def carbon_aware_policy(ctx: dict[str, Any]) -> dict[str, Any]:
    bat = ctx.get("battery", {}) or {}
    dc = ctx.get("data_center", {}) or {}
    pv = ctx.get("fronius", {}) or {}
    grid = ctx.get("grid", {}) or {}

    ci = float(grid.get("CI_gco2_kwh", 500.0))
    online = bool(grid.get("online", True))
    soc = float(bat.get("SOC", 0.5))
    load = float(dc.get("P_total", 0.0))
    pv_p = float(pv.get("P_ac", 0.0))

    if not online:
        return {
            "fronius_setpoint_pct": 1.0,
            "quattro_mode": "off-grid",
            "quattro_command_w": -min(max(load - pv_p, 0.0), 4500.0),
            "generator_enable": soc < 0.25,
            "generator_request_w": max(load - pv_p, 0.0),
            "dcdc_enable": soc < 0.25,
            "mts_position": "generator" if soc < 0.25 else "inverter",
            "chroma_mode": "load", "chroma_power_w": 0.0,
        }

    if ci > 550 and soc > 0.35:
        cmd = -min(max(load - pv_p, 0.0), 3500.0)
    elif ci < 350 and soc < 0.85:
        cmd = +min(2500.0, max(pv_p - load, 0.0) + 500.0)
    else:
        cmd = 0.0
    return {
        "fronius_setpoint_pct": 1.0,
        "quattro_mode": "grid-tied",
        "quattro_command_w": cmd,
        "generator_enable": False, "generator_request_w": 0.0,
        "dcdc_enable": False, "mts_position": "inverter",
        "chroma_mode": "load", "chroma_power_w": 0.0,
    }
