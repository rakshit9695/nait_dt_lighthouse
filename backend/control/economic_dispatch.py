"""Economic dispatch via single-step LP (spec §2.2.13.2)."""
from __future__ import annotations

from typing import Any

import pulp


def economic_dispatch_policy(ctx: dict[str, Any]) -> dict[str, Any]:
    bat = ctx.get("battery", {}) or {}
    dc = ctx.get("data_center", {}) or {}
    pv = ctx.get("fronius", {}) or {}
    grid = ctx.get("grid", {}) or {}

    lmp = float(grid.get("LMP", 60.0))
    online = bool(grid.get("online", True))
    soc = float(bat.get("SOC", 0.5))
    load = float(dc.get("P_total", 0.0))
    pv_p = float(pv.get("P_ac", 0.0))

    prob = pulp.LpProblem("dispatch", pulp.LpMinimize)
    bd = pulp.LpVariable("bat_disch", lowBound=0.0, upBound=5000.0)
    bc = pulp.LpVariable("bat_chg", lowBound=0.0, upBound=3000.0)
    gi = pulp.LpVariable("grid_import", lowBound=0.0, upBound=10000.0 if online else 0.0)
    ge = pulp.LpVariable("grid_export", lowBound=0.0, upBound=5000.0 if online else 0.0)
    cycle_cost = 20.0  # $/MWh-throughput proxy
    prob += (lmp / 1000.0) * gi - 0.8 * (lmp / 1000.0) * ge + cycle_cost * (bc + bd) / 1000.0
    prob += pv_p + bd + gi == load + bc + ge
    if soc <= 0.15:
        prob += bd == 0
    if soc >= 0.90:
        prob += bc == 0
    prob.solve(pulp.PULP_CBC_CMD(msg=False))

    bd_v = float(bd.value() or 0.0)
    bc_v = float(bc.value() or 0.0)
    quattro_cmd = bc_v - bd_v
    return {
        "fronius_setpoint_pct": 1.0,
        "quattro_mode": "grid-tied" if online else "off-grid",
        "quattro_command_w": quattro_cmd,
        "generator_enable": (not online) and soc < 0.20,
        "generator_request_w": max(0.0, load - pv_p - bd_v) if not online else 0.0,
        "dcdc_enable": (not online) and soc < 0.20,
        "mts_position": "generator" if (not online and soc < 0.20) else "inverter",
        "chroma_mode": "load",
        "chroma_power_w": 0.0,
    }
