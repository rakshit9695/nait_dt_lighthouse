"""Rule-based baseline controller (spec §2.2.13.1)."""
from __future__ import annotations

from typing import Any


def rule_baseline_policy(ctx: dict[str, Any]) -> dict[str, Any]:
    bat = ctx.get("battery", {}) or {}
    dc = ctx.get("data_center", {}) or {}
    pv = ctx.get("fronius", {}) or {}
    grid = ctx.get("grid", {}) or {}

    soc = float(bat.get("SOC", 0.5))
    load = float(dc.get("P_total", 0.0))
    pv_p = float(pv.get("P_ac", 0.0))
    deficit = load - pv_p
    online = bool(grid.get("online", True))

    quattro_cmd = 0.0
    mode = "grid-tied" if online else "off-grid"
    gen_enable = False
    gen_req = 0.0
    mts_pos = "inverter"
    dcdc_enable = False

    if not online:
        if soc > 0.20:
            quattro_cmd = -min(max(deficit, 0.0), 4500.0)
        else:
            gen_enable = True
            dcdc_enable = True
            gen_req = min(max(deficit, 1000.0), 3000.0)
            mts_pos = "generator"
            quattro_cmd = -min(max(deficit - gen_req, 0.0), 2500.0)
    else:
        # Grid-tied: charge when SOC<50% and PV surplus, discharge when load > PV+2kW and SOC>70%
        if soc < 0.50 and pv_p > load:
            quattro_cmd = +min(pv_p - load, 2000.0)
        elif soc > 0.70 and deficit > 2000.0:
            quattro_cmd = -min(deficit, 3000.0)

    return {
        "fronius_setpoint_pct": 1.0,
        "quattro_mode": mode,
        "quattro_command_w": quattro_cmd,
        "generator_enable": gen_enable,
        "generator_request_w": gen_req,
        "dcdc_enable": dcdc_enable,
        "mts_position": mts_pos,
        "chroma_mode": "load",
        "chroma_power_w": 0.0,
    }
