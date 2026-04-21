"""Typed JSON contracts shared across backend / frontend (spec §8)."""
from __future__ import annotations

from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field

ComponentType = Literal[
    "pv_sim", "inverter", "battery", "bidir_inverter",
    "system_controller", "dcdc", "generator", "mts",
    "panel", "load_sim", "data_center", "grid_tie", "plc",
]
ControlPolicy = Literal["rule_baseline", "economic", "carbon_aware", "external"]


class AssumptionRef(BaseModel):
    param: str
    default_value: float | str | bool
    unit: str
    source_doc: str = "Questions_for_NAIT.pdf"
    question_index: int = 0
    confidence_penalty: float = Field(0.1, ge=0.0, le=1.0)


class ComponentState(BaseModel):
    component_id: str
    type: ComponentType
    timestamp: datetime
    state: dict[str, Any]
    assumptions: list[AssumptionRef] = Field(default_factory=list)
    faults: list[str] = Field(default_factory=list)


class TimeStepRecord(BaseModel):
    timestamp: datetime
    component_id: str
    P_ac_W: float = 0.0
    P_dc_W: float = 0.0
    V_ac_V: float = 0.0
    V_dc_V: float = 0.0
    I_A: float = 0.0
    SOC: float | None = None
    T_C: float | None = None
    status: str = "ok"


class FlowRecord(BaseModel):
    model_config = ConfigDict(populate_by_name=True)
    source: str = Field(alias="from")
    target: str = Field(alias="to")
    P_W: float


class WSFrame(BaseModel):
    t: datetime
    dt: float
    components: dict[str, dict[str, Any]]
    flows: list[dict[str, Any]]


class WorkloadHourMix(BaseModel):
    hour: int
    mix: dict[str, float]


class ScenarioDrivers(BaseModel):
    irradiance_W_m2: list[float]
    ambient_temp_C: list[float]
    grid_LMP_usd_MWh: list[float]
    grid_CO2_gco2_kwh: list[float]
    IT_load_kW: list[float]
    grid_online: list[bool]
    workload_mix: list[WorkloadHourMix]


class ScenarioInitial(BaseModel):
    battery_SOC: float = 0.5
    fuel_kg: float = 20.0
    grid_online: bool = True


class Scenario(BaseModel):
    id: str
    name: str
    horizon_hours: int = Field(48, ge=1, le=168)
    resolution_seconds: int = 3600
    drivers: ScenarioDrivers
    control_policy: ControlPolicy = "rule_baseline"
    initial_state: ScenarioInitial = Field(default_factory=ScenarioInitial)


class CommandEnvelope(BaseModel):
    component_id: str
    command: dict[str, Any]


class ComponentEvaluation(BaseModel):
    id: str
    C_i: float
    physical_consistency: float
    empirical_match: float
    assumption_density: float
    details: dict[str, Any] = Field(default_factory=dict)


class EvaluationReport(BaseModel):
    run_id: str
    scenario_id: str
    dt_confidence: float
    components: list[ComponentEvaluation]
    system_metrics: dict[str, float]
    generated_at: datetime


class ScenarioRunSummary(BaseModel):
    run_id: str
    scenario_id: str
    started_at: datetime
    completed_at: datetime
    n_steps: int
    evaluation: EvaluationReport
    series: dict[str, list[dict[str, Any]]]  # per-component time series
    flows: list[list[dict[str, Any]]]  # per-step flow snapshots
