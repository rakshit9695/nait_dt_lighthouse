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
        # Grid-tied: keep the battery actively cycling so the storage path is
        # visible. Charge whenever PV surplus exists and SOC headroom remains;
        # discharge whenever a deficit exists and the battery has reserve.
        surplus = pv_p - load
        if surplus > 100.0 and soc < 0.95:
            # Soft taper near full: scale charge by remaining headroom
            headroom = max(0.0, (0.95 - soc) / 0.45)
            quattro_cmd = +min(surplus, 3000.0) * min(1.0, max(0.2, headroom))
        elif deficit > 100.0 and soc > 0.25:
            reserve = max(0.0, (soc - 0.25) / 0.45)
            quattro_cmd = -min(deficit, 3000.0) * min(1.0, max(0.2, reserve))

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
