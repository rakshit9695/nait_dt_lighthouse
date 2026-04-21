"""Generate the 8 canned scenario YAML files (spec §5.2)."""
from __future__ import annotations

import math
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "scenarios" / "canned"
OUT.mkdir(parents=True, exist_ok=True)


def daily_irradiance(h: int, peak: float = 1000.0) -> float:
    hod = h % 24
    if 6 <= hod <= 18:
        return max(0.0, peak * math.sin(math.pi * (hod - 6) / 12.0))
    return 0.0


def base_workload(hours: int, mix: dict[str, float] | None = None):
    default = {"web_serving": 0.4, "agentic": 0.2, "training": 0.2,
               "llm_inference": 0.1, "batch_hpc": 0.1}
    return [{"hour": h, "mix": mix or default} for h in range(hours)]


def scenario(sid: str, name: str, hours: int, *, irr, ambient, lmp, co2, it_load,
             grid_online, mix=None, policy="rule_baseline",
             initial_soc=0.5, fuel_kg=20.0):
    return {
        "scenario": {
            "id": sid, "name": name,
            "horizon_hours": hours, "resolution_seconds": 3600,
            "control_policy": policy,
            "initial_state": {"battery_SOC": initial_soc, "fuel_kg": fuel_kg,
                              "grid_online": True},
            "drivers": {
                "irradiance_W_m2": irr, "ambient_temp_C": ambient,
                "grid_LMP_usd_MWh": lmp, "grid_CO2_gco2_kwh": co2,
                "IT_load_kW": it_load, "grid_online": grid_online,
                "workload_mix": base_workload(hours, mix),
            },
        }
    }


def write(s: dict) -> None:
    sid = s["scenario"]["id"]
    (OUT / f"{sid}.yaml").write_text(yaml.safe_dump(s, sort_keys=False), encoding="utf-8")


def gen() -> None:
    H = 72
    H48 = 48
    sunny_irr = [daily_irradiance(h, 1000.0) for h in range(H)]
    cloudy_irr = [daily_irradiance(h, 350.0) for h in range(H48)]
    ambient_norm = [22.0 + 5.0 * math.sin(2 * math.pi * (h - 14) / 24.0) for h in range(H)]
    lmp_flat = [60.0] * H
    co2_flat = [400.0] * H
    it_flat = [2.5 + 0.5 * math.sin(2 * math.pi * (h - 14) / 24.0) for h in range(H)]
    online_all = [True] * H

    write(scenario("sunny_grid_stable", "Sunny day, stable grid", H,
                   irr=sunny_irr, ambient=ambient_norm[:H], lmp=lmp_flat,
                   co2=co2_flat, it_load=it_flat, grid_online=online_all))

    write(scenario("cloudy_grid_stable", "Cloudy day, stable grid", H48,
                   irr=cloudy_irr, ambient=ambient_norm[:H48], lmp=lmp_flat[:H48],
                   co2=co2_flat[:H48], it_load=it_flat[:H48], grid_online=[True] * H48))

    outage_irr = [daily_irradiance(h, 1000.0) for h in range(H48)]
    outage_grid = [True] * H48
    for h in range(11, 15):  # 4-hour outage spanning solar noon
        outage_grid[h] = False
    write(scenario("grid_outage_noon", "Grid outage at solar noon", H48,
                   irr=outage_irr, ambient=ambient_norm[:H48], lmp=lmp_flat[:H48],
                   co2=co2_flat[:H48], it_load=it_flat[:H48], grid_online=outage_grid))

    spike_lmp = list(lmp_flat[:H48])
    for h in range(17, 21):
        spike_lmp[h] = 800.0
    write(scenario("price_spike_evening", "Evening LMP spike", H48,
                   irr=cloudy_irr, ambient=ambient_norm[:H48], lmp=spike_lmp,
                   co2=co2_flat[:H48], it_load=it_flat[:H48],
                   grid_online=[True] * H48, policy="economic"))

    co2_night = [800.0 if (h % 24) < 6 or (h % 24) > 20 else 250.0 for h in range(H48)]
    write(scenario("carbon_high_night", "High overnight carbon intensity", H48,
                   irr=sunny_irr[:H48], ambient=ambient_norm[:H48], lmp=lmp_flat[:H48],
                   co2=co2_night, it_load=it_flat[:H48],
                   grid_online=[True] * H48, policy="carbon_aware"))

    heat_amb = [38.0 + 4.0 * math.sin(2 * math.pi * (h - 14) / 24.0) for h in range(H48)]
    write(scenario("heatwave", "42°C heatwave thermal stress", H48,
                   irr=sunny_irr[:H48], ambient=heat_amb, lmp=lmp_flat[:H48],
                   co2=co2_flat[:H48], it_load=it_flat[:H48],
                   grid_online=[True] * H48))

    burst_load = [3.5 if 9 <= (h % 24) <= 17 else 1.5 for h in range(H48)]
    burst_mix = {"web_serving": 0.05, "agentic": 0.05, "training": 0.6,
                 "llm_inference": 0.2, "batch_hpc": 0.1}
    write(scenario("ai_training_burst", "AI training burst workload", H48,
                   irr=sunny_irr[:H48], ambient=ambient_norm[:H48], lmp=lmp_flat[:H48],
                   co2=co2_flat[:H48], it_load=burst_load, grid_online=[True] * H48,
                   mix=burst_mix))

    worst_grid = [True] * H48
    for h in range(20, 32):
        worst_grid[h] = False
    write(scenario("worst_case", "Worst case: heatwave + outage + spike + AI burst",
                   H48,
                   irr=cloudy_irr[:H48], ambient=heat_amb,
                   lmp=[900.0 if 16 <= (h % 24) <= 21 else 80.0 for h in range(H48)],
                   co2=[750.0] * H48, it_load=burst_load, grid_online=worst_grid,
                   mix=burst_mix, initial_soc=0.35, fuel_kg=15.0))


if __name__ == "__main__":
    gen()
    print(f"Wrote scenarios to {OUT}")
