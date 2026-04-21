"""Rule-based baseline controller (spec §2.2.13.1)."""
from __future__ import annotations

from typing import Any


DC_AUX_HOUSE_LOAD_W = 250.0
GEN_EXERCISE_HOUR = 3
GEN_EXERCISE_POWER_W = 600.0


def rule_baseline_policy(ctx: dict[str, Any]) -> dict[str, Any]:
    bat = ctx.get("battery", {}) or {}
    dc = ctx.get("data_center", {}) or {}
    pv = ctx.get("fronius", {}) or {}
    grid = ctx.get("grid", {}) or {}
    hour_of_day = int(ctx.get("hour_of_day", 0))
    fuel_kg = float(ctx.get("generator", {}).get("fuel_kg_remaining", 1.0))

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
    # DC-DC always enabled: when generator runs it relays gen→battery; otherwise it
    # serves a small DC house load (instrumentation, lighting, controls) from the
    # battery so the DC distribution path is always observable.
    dcdc_enable = True
    dc_aux_load_w = DC_AUX_HOUSE_LOAD_W

    if not online:
        if soc > 0.20:
            quattro_cmd = -min(max(deficit, 0.0), 4500.0)
        else:
            gen_enable = True
            gen_req = min(max(deficit, 1000.0), 3000.0)
            mts_pos = "generator"
            quattro_cmd = -min(max(deficit - gen_req, 0.0), 2500.0)
    else:
        # Daily generator exercise (anti wet-stacking / readiness check) at
        # GEN_EXERCISE_HOUR for one hour at low power. Skipped if fuel is empty.
        if hour_of_day == GEN_EXERCISE_HOUR and fuel_kg > 0.05:
            gen_enable = True
            gen_req = GEN_EXERCISE_POWER_W
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
        "dc_aux_load_w": dc_aux_load_w,
        "mts_position": mts_pos,
        "chroma_mode": "load",
        "chroma_power_w": 0.0,
    }
