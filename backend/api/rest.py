"""REST endpoints (spec §3.1)."""
from __future__ import annotations

import os
import time
from collections import defaultdict
from datetime import datetime, timezone
from typing import Any

from fastapi import APIRouter, Depends, Header, HTTPException

from backend.configuration import all_assumptions, load_topology
from backend.contracts import CommandEnvelope, Scenario
from backend.control.external_hook import set_external
from backend.solver.safety import clip_command
from backend.solver.simulator import SIMULATOR

router = APIRouter(prefix="/api/v1")
_LAST_CMD: dict[str, float] = defaultdict(float)
_SAFETY_LOG: list[dict[str, Any]] = []


def require_token(authorization: str | None = Header(default=None)) -> None:
    expected = os.getenv("NAIT_DT_TOKEN", "dev-token")
    if authorization != f"Bearer {expected}":
        raise HTTPException(status_code=401, detail="Unauthorized")


@router.get("/topology", dependencies=[Depends(require_token)])
def get_topology() -> dict[str, Any]:
    SIMULATOR.ensure_live_state()
    return load_topology()


@router.get("/components", dependencies=[Depends(require_token)])
def get_components() -> list[dict[str, Any]]:
    SIMULATOR.ensure_live_state()
    return [c.model_dump(mode="json") for c in SIMULATOR.latest_components.values()]


@router.get("/components/{cid}", dependencies=[Depends(require_token)])
def get_component(cid: str) -> dict[str, Any]:
    SIMULATOR.ensure_live_state()
    c = SIMULATOR.latest_components.get(cid)
    if c is None:
        raise HTTPException(404, "component not found")
    return c.model_dump(mode="json")


@router.get("/components/{cid}/history", dependencies=[Depends(require_token)])
def get_history(cid: str, since: str | None = None) -> list[dict[str, Any]]:
    series: list[dict[str, Any]] = []
    for run in SIMULATOR.runs.values():
        if cid in run.series:
            series.extend(run.series[cid])
    if since:
        try:
            cutoff = datetime.fromisoformat(since.replace("Z", "+00:00"))
            series = [s for s in series if datetime.fromisoformat(s["t"].replace("Z", "+00:00")) >= cutoff]
        except ValueError:
            raise HTTPException(400, "invalid since format")
    return series


@router.post("/components/{cid}/command", dependencies=[Depends(require_token)])
def command(cid: str, env: CommandEnvelope) -> dict[str, Any]:
    now = time.time()
    if now - _LAST_CMD[cid] < 1.0:
        raise HTTPException(429, "rate limited (1 command/sec/component)")
    _LAST_CMD[cid] = now
    clipped, violations = clip_command(cid, env.command)
    entry = {"timestamp": datetime.now(timezone.utc).isoformat(),
             "component_id": cid, "requested": env.command,
             "applied": clipped, "violations": violations}
    if violations:
        _SAFETY_LOG.append(entry)
    return entry


@router.get("/safety/log", dependencies=[Depends(require_token)])
def safety_log() -> list[dict[str, Any]]:
    return list(_SAFETY_LOG)


@router.get("/assumptions", dependencies=[Depends(require_token)])
def assumptions() -> list[dict[str, Any]]:
    return [a.model_dump(mode="json") for a in all_assumptions()]


@router.get("/scenarios", dependencies=[Depends(require_token)])
def list_scenarios() -> list[dict[str, Any]]:
    return [s.model_dump(mode="json") for s in SIMULATOR.list_scenarios()]


@router.get("/scenarios/{sid}", dependencies=[Depends(require_token)])
def get_scenario(sid: str) -> dict[str, Any]:
    s = SIMULATOR.get_scenario(sid)
    if s is None:
        raise HTTPException(404, "scenario not found")
    return s.model_dump(mode="json")


@router.post("/scenarios", dependencies=[Depends(require_token)])
def create_scenario(s: Scenario) -> dict[str, Any]:
    return SIMULATOR.create_scenario(s).model_dump(mode="json")


@router.post("/scenarios/{sid}/run", dependencies=[Depends(require_token)])
def run_scenario(sid: str) -> dict[str, Any]:
    if sid not in SIMULATOR.scenarios:
        raise HTTPException(404, "scenario not found")
    summary = SIMULATOR.run_scenario(sid)
    return summary.model_dump(mode="json")


@router.get("/scenarios/{sid}/results", dependencies=[Depends(require_token)])
def scenario_results(sid: str) -> list[dict[str, Any]]:
    return [r.model_dump(mode="json") for r in SIMULATOR.runs.values() if r.scenario_id == sid]


@router.get("/evaluation/{run_id}", dependencies=[Depends(require_token)])
def evaluation(run_id: str) -> dict[str, Any]:
    run = SIMULATOR.runs.get(run_id)
    if run is None:
        raise HTTPException(404, "run not found")
    return run.evaluation.model_dump(mode="json")


@router.post("/policy/external", dependencies=[Depends(require_token)])
def push_policy(commands: dict[str, Any]) -> dict[str, Any]:
    return {"status": "accepted", "commands": set_external(commands)}
