"""Simulator service: orchestrates scenario runs and live state (spec §2.1, §6.3)."""
from __future__ import annotations

import math
from collections import defaultdict, deque
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any
from uuid import uuid4

import yaml

from backend.configuration import ROOT, load_topology
from backend.contracts import (
    ComponentState, EvaluationReport, Scenario, ScenarioRunSummary, WSFrame,
)
from backend.eval.report import write_report
from backend.eval.scorer import build_report, summarize_metrics
from backend.solver.network_solver import NetworkSolver
from backend.solver.persistence import append_records


def _build_default_drivers(horizon: int) -> dict[str, list]:
    """Generate a baseline 48-h driver set for live-mode bootstrap."""
    irr = [max(0.0, 1000.0 * math.sin(math.pi * (h % 24 - 6) / 12.0)) if 6 <= h % 24 <= 18 else 0.0
           for h in range(horizon)]
    amb = [22.0 + 5.0 * math.sin(2 * math.pi * (h - 14) / 24.0) for h in range(horizon)]
    return {
        "irradiance_W_m2": irr,
        "ambient_temp_C": amb,
        "grid_LMP_usd_MWh": [60.0] * horizon,
        "grid_CO2_gco2_kwh": [400.0] * horizon,
        "IT_load_kW": [2.0 + 0.5 * math.sin(2 * math.pi * (h - 14) / 24.0) for h in range(horizon)],
        "grid_online": [True] * horizon,
        "workload_mix": [{"hour": h, "mix": {"web_serving": 0.4, "agentic": 0.2,
                                              "training": 0.2, "llm_inference": 0.1, "batch_hpc": 0.1}}
                         for h in range(horizon)],
    }


class SimulatorService:
    def __init__(self) -> None:
        self.topology = load_topology()
        self.scenarios: dict[str, Scenario] = {}
        self.runs: dict[str, ScenarioRunSummary] = {}
        self.live_buffer: deque[WSFrame] = deque(maxlen=1000)
        self.latest_components: dict[str, ComponentState] = {}
        self.latest_flows: list[dict[str, Any]] = []
        self.history: dict[str, list[dict[str, Any]]] = defaultdict(list)
        self._load_canned()

    def _load_canned(self) -> None:
        d = ROOT / "scenarios" / "canned"
        if not d.exists():
            return
        for p in d.glob("*.yaml"):
            data = yaml.safe_load(p.read_text(encoding="utf-8"))
            sc = Scenario.model_validate(data["scenario"])
            self.scenarios[sc.id] = sc
        for p in (ROOT / "scenarios" / "user").glob("*.yaml"):
            data = yaml.safe_load(p.read_text(encoding="utf-8"))
            sc = Scenario.model_validate(data["scenario"])
            self.scenarios[sc.id] = sc

    def list_scenarios(self) -> list[Scenario]:
        return [s for sid, s in self.scenarios.items() if not sid.startswith("_")]

    def get_scenario(self, sid: str) -> Scenario | None:
        return self.scenarios.get(sid)

    def create_scenario(self, sc: Scenario) -> Scenario:
        self.scenarios[sc.id] = sc
        out = ROOT / "scenarios" / "user" / f"{sc.id}.yaml"
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(yaml.safe_dump({"scenario": sc.model_dump(mode="json")}, sort_keys=False),
                       encoding="utf-8")
        return sc

    def run_scenario(self, sid: str) -> ScenarioRunSummary:
        sc = self.scenarios[sid]
        solver = NetworkSolver(policy=sc.control_policy,
                               initial_soc=sc.initial_state.battery_SOC,
                               initial_fuel_kg=sc.initial_state.fuel_kg)
        # Honor initial grid_online by writing into solver.grid; first-step driver wins anyway.
        start = datetime.now(timezone.utc)
        ts = start
        dt = float(sc.resolution_seconds)
        all_records = []
        summaries = []
        series: dict[str, list[dict[str, Any]]] = defaultdict(list)
        flows_per_step: list[list[dict[str, Any]]] = []
        for h in range(sc.horizon_hours):
            wm = sc.drivers.workload_mix[h].mix if h < len(sc.drivers.workload_mix) else \
                {"web_serving": 1.0}
            drivers = {
                "hour": h,
                "irradiance_W_m2": sc.drivers.irradiance_W_m2[h],
                "ambient_temp_C": sc.drivers.ambient_temp_C[h],
                "grid_LMP_usd_MWh": sc.drivers.grid_LMP_usd_MWh[h],
                "grid_CO2_gco2_kwh": sc.drivers.grid_CO2_gco2_kwh[h],
                "IT_load_kW": sc.drivers.IT_load_kW[h],
                "grid_online": sc.drivers.grid_online[h],
                "workload_mix": wm,
            }
            recs, summary = solver.step(ts, dt, drivers, sc.control_policy)
            all_records.extend(recs)
            summaries.append(summary)
            flows_per_step.append(summary["flows"])
            for cid, cs in summary["components"].items():
                series[cid].append({"t": ts.isoformat(), **{k: v for k, v in cs.items()
                                                              if isinstance(v, (int, float, bool, str))}})
            self.latest_components = {c.component_id: c.snapshot(ts) for c in solver.components}
            self.latest_flows = summary["flows"]
            self.live_buffer.append(WSFrame(t=ts, dt=dt, components=summary["components"],
                                              flows=summary["flows"]))
            ts += timedelta(seconds=dt)

        sys_metrics = summarize_metrics(summaries)
        snaps = {c.component_id: c.snapshot().model_dump(mode="json")
                 for c in solver.components}
        report = build_report(str(uuid4()), sc.id, snaps, sys_metrics)
        out_dir = ROOT / "eval"
        write_report(report, out_dir)
        append_records(report.run_id, all_records, ROOT)
        summary = ScenarioRunSummary(
            run_id=report.run_id, scenario_id=sc.id,
            started_at=start, completed_at=ts, n_steps=sc.horizon_hours,
            evaluation=report, series=dict(series), flows=flows_per_step,
        )
        self.runs[report.run_id] = summary
        return summary

    def ensure_live_state(self) -> None:
        if self.latest_components:
            return
        if "sunny_grid_stable" in self.scenarios:
            sid = "sunny_grid_stable"
        elif self.scenarios:
            sid = next(iter(self.scenarios))
        else:
            return
        sc = self.scenarios[sid]
        # Run only first hour for live bootstrap (cheap)
        live_id = f"_live_{sid}"
        live = sc.model_copy(deep=True)
        live.id = live_id
        live.horizon_hours = 1
        for field in ("irradiance_W_m2", "ambient_temp_C", "grid_LMP_usd_MWh",
                      "grid_CO2_gco2_kwh", "IT_load_kW", "grid_online"):
            setattr(live.drivers, field, getattr(sc.drivers, field)[:1])
        live.drivers.workload_mix = sc.drivers.workload_mix[:1]
        self.scenarios[live_id] = live
        self.run_scenario(live_id)


SIMULATOR = SimulatorService()
