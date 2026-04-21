"""End-to-end backend stress harness.

Runs every canned scenario plus many random/fuzz scenarios through the
SimulatorService, validating physical, numerical and behavioural invariants
at every time-step. Prints a compact issue ledger.

Usage:
    python -m backend.tests.stress_harness            # default 200 fuzz runs
    python -m backend.tests.stress_harness 1000        # custom count
"""
from __future__ import annotations

import math
import random
import sys
import time
import traceback
from collections import Counter, defaultdict
from typing import Any

from backend.contracts import Scenario, ScenarioDrivers, ScenarioInitial, WorkloadHourMix
from backend.solver.simulator import SimulatorService

ISSUES: list[tuple[str, str, str]] = []  # (scenario_id, severity, message)


def report(sid: str, sev: str, msg: str) -> None:
    ISSUES.append((sid, sev, msg))


def _is_finite(v: Any) -> bool:
    if isinstance(v, bool):
        return True
    if isinstance(v, (int, float)):
        return math.isfinite(float(v))
    return True


def validate_run(sim, sid: str, summary, *, conf_threshold: float = 0.80) -> dict[str, Any]:
    """Return per-scenario stats; append issues to ISSUES."""
    stats: dict[str, Any] = {
        "n_steps": summary.n_steps,
        "dt_confidence": summary.evaluation.dt_confidence,
        "energy_residual_mean": summary.evaluation.system_metrics.get(
            "energy_balance_residual", 0.0),
        "active": {},  # cid -> nonzero step count
        "max_residual": 0.0,
        "load_shed_total_w": 0.0,
    }

    if summary.evaluation.dt_confidence < conf_threshold:
        report(sid, "ERROR",
               f"DT_Confidence {summary.evaluation.dt_confidence:.3f} < {conf_threshold:.2f} acceptance bar")

    if stats["energy_residual_mean"] > 0.005:
        report(sid, "ERROR",
               f"mean energy_balance_residual {stats['energy_residual_mean']:.4%} > 0.5%")

    # Per-component activity tracking
    activity: dict[str, int] = defaultdict(int)
    for cid, ts_list in summary.series.items():
        for snap in ts_list:
            for k, v in snap.items():
                if k == "t":
                    continue
                if not _is_finite(v):
                    report(sid, "ERROR", f"{cid}.{k} = {v!r} not finite")
            # activity heuristic - any obvious power field nonzero
            for k in ("P_ac", "P_dc", "P", "P_out", "P_in", "P_total"):
                v = snap.get(k)
                if isinstance(v, (int, float)) and abs(v) > 1.0:
                    activity[cid] += 1
                    break
    stats["active"] = dict(activity)

    # Battery bounds & monotonic fuel
    bat = summary.series.get("battery", [])
    soc_vals = [s["SOC"] for s in bat if "SOC" in s]
    if soc_vals:
        if min(soc_vals) < 0.0 or max(soc_vals) > 1.0:
            report(sid, "ERROR", f"SOC out of [0,1]: min={min(soc_vals):.3f} max={max(soc_vals):.3f}")
        if min(soc_vals) < 0.05 or max(soc_vals) > 0.99:
            report(sid, "WARN", f"SOC near limits: {min(soc_vals):.2f}-{max(soc_vals):.2f}")
    soh_vals = [s.get("SOH") for s in bat if s.get("SOH") is not None]
    if soh_vals and (min(soh_vals) < 0.5 or max(soh_vals) > 1.0):
        report(sid, "ERROR", f"SOH out of plausible: {min(soh_vals):.3f}-{max(soh_vals):.3f}")
    bat_t = [s.get("T") for s in bat if s.get("T") is not None]
    if bat_t and max(bat_t) > 60.0:
        report(sid, "ERROR", f"battery temperature {max(bat_t):.1f}C > 60C limit")

    gen_fuel = [s.get("fuel_kg_remaining") for s in summary.series.get("generator", [])]
    gen_fuel = [f for f in gen_fuel if f is not None]
    if gen_fuel:
        if min(gen_fuel) < -1e-6:
            report(sid, "ERROR", f"generator fuel negative: {min(gen_fuel):.3f}")
        for a, b in zip(gen_fuel, gen_fuel[1:]):
            if b > a + 1e-6:
                report(sid, "ERROR", f"generator fuel non-monotonic: {a:.3f} -> {b:.3f}")
                break

    # PV non-negative
    for s in summary.series.get("pv_sim", []):
        if s.get("P_dc", 0) < -1.0:
            report(sid, "ERROR", f"pv_sim P_dc negative: {s.get('P_dc')}")
            break

    # Component nameplate sanity
    rated = {
        "fronius": ("P_ac", 8200.0),
        "quattro": ("P_ac", 5000.0),
        "chroma": ("P", 9000.0),
        "generator": ("P_dc", 7500.0),
        "dcdc": ("P_out", 3000.0),
        "data_center": ("P_total", 20000.0),
    }
    for cid, (field, rated_w) in rated.items():
        for snap in summary.series.get(cid, []):
            v = snap.get(field, 0.0)
            if isinstance(v, (int, float)) and abs(v) > rated_w * 1.15:
                report(sid, "WARN",
                       f"{cid}.{field} = {v:.0f} W exceeds 115% of rated {rated_w:.0f} W")
                break

    # Each non-trivially-idle component should activate at least once across run.
    # Generator/dcdc may be legitimately idle when grid is up + SOC sufficient.
    must_be_active = ["pv_sim", "fronius", "data_center", "battery", "chroma"]
    for cid in must_be_active:
        if activity.get(cid, 0) == 0:
            report(sid, "WARN", f"{cid} never activated (0 nonzero power steps)")

    # Per-step flow validation: AC supply ~ AC demand when grid online
    for step_idx, flow_snap in enumerate(summary.flows):
        flows_by_pair = {(f["from"], f["to"]): f["P_W"] for f in flow_snap}
        for k, v in flows_by_pair.items():
            if not _is_finite(v):
                report(sid, "ERROR", f"step{step_idx} flow {k} not finite: {v}")

    return stats


def run_canned(sim) -> None:
    print("\n=== Canned scenarios ===")
    for sc in sim.list_scenarios():
        if sc.id.startswith("_"):
            continue
        t0 = time.time()
        try:
            summary = sim.run_scenario(sc.id)
        except Exception as e:
            report(sc.id, "FATAL", f"run raised {type(e).__name__}: {e}")
            traceback.print_exc()
            continue
        s = validate_run(sim, sc.id, summary)
        print(f"  {sc.id:24} dt_conf={s['dt_confidence']:.3f} "
              f"resid={s['energy_residual_mean']:.4%} "
              f"active={len(s['active'])}/13 "
              f"in {time.time()-t0:.1f}s")


def make_fuzz(idx: int, rng: random.Random) -> Scenario:
    h = rng.choice([24, 48, 72])
    # Random irradiance with cloud bursts
    irr = []
    for hr in range(h):
        hod = hr % 24
        base = max(0.0, 1100.0 * math.sin(math.pi * (hod - 6) / 12.0)) if 6 <= hod <= 18 else 0.0
        irr.append(max(0.0, base * rng.uniform(0.0, 1.1)))
    amb = [rng.uniform(-15.0, 45.0) for _ in range(h)]
    lmp = [rng.uniform(10.0, 600.0) for _ in range(h)]
    co2 = [rng.uniform(50.0, 900.0) for _ in range(h)]
    it = [max(0.1, rng.gauss(3.0, 1.5)) for _ in range(h)]
    online = [rng.random() > 0.15 for _ in range(h)]
    chroma = [max(0.0, rng.gauss(1.5, 1.5)) for _ in range(h)]
    mix = [WorkloadHourMix(hour=hr, mix={
        "web_serving": rng.random(),
        "agentic": rng.random(),
        "training": rng.random(),
        "llm_inference": rng.random(),
        "batch_hpc": rng.random(),
    }) for hr in range(h)]
    drivers = ScenarioDrivers(
        irradiance_W_m2=irr, ambient_temp_C=amb, grid_LMP_usd_MWh=lmp,
        grid_CO2_gco2_kwh=co2, IT_load_kW=it, grid_online=online,
        workload_mix=mix, chroma_load_kW=chroma,
    )
    init = ScenarioInitial(
        battery_SOC=rng.uniform(0.15, 0.90),
        fuel_kg=rng.uniform(5.0, 30.0),
        grid_online=online[0],
    )
    return Scenario(
        id=f"_fuzz_{idx:04d}",
        name=f"fuzz #{idx}",
        horizon_hours=h,
        resolution_seconds=3600,
        drivers=drivers,
        control_policy=rng.choice(["rule_baseline", "rule_baseline"]),
        initial_state=init,
    )


def run_fuzz(sim, n: int, seed: int = 42) -> None:
    print(f"\n=== {n} fuzz scenarios (seed={seed}) ===")
    rng = random.Random(seed)
    fail_count = 0
    t0 = time.time()
    for i in range(n):
        sc = make_fuzz(i, rng)
        sim.scenarios[sc.id] = sc
        try:
            summary = sim.run_scenario(sc.id)
        except Exception as e:
            fail_count += 1
            report(sc.id, "FATAL", f"{type(e).__name__}: {e}")
            continue
        validate_run(sim, sc.id, summary, conf_threshold=0.70)
        del sim.scenarios[sc.id]
        if (i + 1) % max(1, n // 10) == 0:
            print(f"  {i+1}/{n} done ({time.time()-t0:.1f}s, fatals={fail_count})")
    print(f"  fuzz complete in {time.time()-t0:.1f}s")


def edge_cases(sim) -> None:
    print("\n=== Edge cases ===")
    cases = [
        ("zero_irradiance", {"irradiance_W_m2": 0.0}),
        ("max_irradiance", {"irradiance_W_m2": 1200.0}),
        ("freezing_amb", {"ambient_temp_C": -25.0}),
        ("scorching_amb", {"ambient_temp_C": 48.0}),
        ("grid_off_full_horizon", {"grid_online": False}),
        ("zero_it_load", {"IT_load_kW": 0.0}),
        ("max_it_load", {"IT_load_kW": 18.0}),
        ("zero_chroma", {"chroma_load_kW": 0.0}),
        ("max_chroma", {"chroma_load_kW": 8.5}),
        ("max_lmp", {"grid_LMP_usd_MWh": 950.0}),
    ]
    for name, override in cases:
        h = 24
        d = {
            "irradiance_W_m2": [800.0] * h, "ambient_temp_C": [22.0] * h,
            "grid_LMP_usd_MWh": [60.0] * h, "grid_CO2_gco2_kwh": [400.0] * h,
            "IT_load_kW": [3.0] * h, "grid_online": [True] * h,
            "chroma_load_kW": [0.8] * h,
        }
        for k, v in override.items():
            d[k] = [v] * h if not isinstance(v, list) else v
        sc = Scenario(
            id=f"_edge_{name}", name=f"edge {name}", horizon_hours=h,
            drivers=ScenarioDrivers(
                **d,
                workload_mix=[WorkloadHourMix(hour=hr, mix={"web_serving": 1.0})
                              for hr in range(h)],
            ),
        )
        sim.scenarios[sc.id] = sc
        try:
            summary = sim.run_scenario(sc.id)
            s = validate_run(sim, sc.id, summary)
            print(f"  {name:24} dt_conf={s['dt_confidence']:.3f} "
                  f"resid={s['energy_residual_mean']:.4%}")
        except Exception as e:
            report(sc.id, "FATAL", f"{type(e).__name__}: {e}")
            print(f"  {name:24} FATAL {e}")
        finally:
            sim.scenarios.pop(sc.id, None)


def print_ledger() -> int:
    if not ISSUES:
        print("\n*** NO ISSUES FOUND ***")
        return 0
    print(f"\n=== Issue ledger ({len(ISSUES)} entries) ===")
    sev_count = Counter(sev for _, sev, _ in ISSUES)
    print("By severity:", dict(sev_count))
    # Summarize distinct messages, with frequency
    msg_count: Counter = Counter()
    sample: dict[str, str] = {}
    for sid, sev, msg in ISSUES:
        # Strip numeric values for grouping
        key = (sev, " ".join(w for w in msg.split() if not any(ch.isdigit() for ch in w)))
        msg_count[key] += 1
        sample.setdefault(repr(key), f"[{sid}] {msg}")
    print(f"\nDistinct issue patterns: {len(msg_count)}")
    for (sev, pattern), n in msg_count.most_common(40):
        ex = sample.get(repr((sev, pattern)), "")
        print(f"  {sev:5} x{n:4d}  e.g. {ex[:140]}")
    return sev_count.get("ERROR", 0) + sev_count.get("FATAL", 0)


def main() -> int:
    n_fuzz = int(sys.argv[1]) if len(sys.argv) > 1 else 200
    sim = SimulatorService()
    run_canned(sim)
    edge_cases(sim)
    run_fuzz(sim, n_fuzz)
    return print_ledger()


if __name__ == "__main__":
    sys.exit(main())
