"""Network solver (spec §2.4): orchestrates one time step across all components."""
from __future__ import annotations

from datetime import datetime
from typing import Any

from backend.components.aluma_generator import AlumaPowerGenerator
from backend.components.base import ComponentModel
from backend.components.battery_pytes import PytesBattery
from backend.components.cerbo_gx import CerboGX
from backend.components.chroma_load import Chroma61809
from backend.components.data_center import DataCenter
from backend.components.dcdc_converter import DCDCConverter
from backend.components.fronius_primo import FroniusPrimo
from backend.components.grid_tie import GridTie
from backend.components.mts import ManualTransferSwitch
from backend.components.panel import SplitPhasePanel
from backend.components.plc_controller import SitePLC
from backend.components.pv_simulator import PVSimulator
from backend.components.victron_quattro import VictronQuattro
from backend.contracts import TimeStepRecord


class NetworkSolver:
    def __init__(self, policy: str = "rule_baseline", initial_soc: float = 0.5,
                 initial_fuel_kg: float | None = None) -> None:
        self.pv = PVSimulator()
        self.fronius = FroniusPrimo()
        self.battery = PytesBattery(config={"initial_soc": initial_soc})
        self.quattro = VictronQuattro()
        self.cerbo = CerboGX()
        self.dcdc = DCDCConverter()
        gen_cfg: dict[str, Any] = {}
        if initial_fuel_kg is not None:
            gen_cfg["initial_fuel_kg"] = initial_fuel_kg
        self.generator = AlumaPowerGenerator(config=gen_cfg)
        self.mts = ManualTransferSwitch()
        self.panel = SplitPhasePanel()
        self.chroma = Chroma61809()
        self.data_center = DataCenter()
        self.grid = GridTie()
        self.plc = SitePLC(config={"policy": policy})
        self.components: list[ComponentModel] = [
            self.pv, self.fronius, self.battery, self.quattro, self.cerbo,
            self.dcdc, self.generator, self.mts, self.panel, self.chroma,
            self.data_center, self.grid, self.plc,
        ]
        self.safety_violations = 0

    def by_id(self) -> dict[str, ComponentModel]:
        return {c.component_id: c for c in self.components}

    def _records(self, ts: datetime) -> list[TimeStepRecord]:
        out: list[TimeStepRecord] = []
        for c in self.components:
            s = c.get_state()
            out.append(TimeStepRecord(
                timestamp=ts, component_id=c.component_id,
                P_ac_W=float(s.get("P_ac", s.get("P", 0.0)) or 0.0),
                P_dc_W=float(s.get("P_dc", s.get("P_out", 0.0)) or 0.0),
                V_ac_V=float(s.get("V_ac_out", s.get("V", s.get("voltage_v", 0.0))) or 0.0),
                V_dc_V=float(s.get("V_dc", s.get("V_term", s.get("V_out", 0.0))) or 0.0),
                I_A=float(s.get("I", s.get("I_dc", s.get("I_out", 0.0))) or 0.0),
                SOC=float(s["SOC"]) if s.get("SOC") is not None else None,
                T_C=float(s["T"]) if s.get("T") is not None else (
                    float(s["T_inlet"]) if s.get("T_inlet") is not None else None),
                status=str(s.get("status", s.get("mode", s.get("state", "ok")))),
            ))
        return out

    def step(self, ts: datetime, dt: float, drivers: dict[str, Any],
             policy: str) -> tuple[list[TimeStepRecord], dict[str, Any]]:
        # 1. Drivers / sources
        pv = self.pv.step(dt, {
            "irradiance_W_m2": drivers["irradiance_W_m2"],
            "ambient_temp_C": drivers["ambient_temp_C"],
            "V_dc_command": self.fronius.state.get("V_dc_request", 720.0),
        })
        # When the macrogrid is down, the Quattro forms a 240V split-phase microgrid,
        # so the Fronius still has a valid AC reference (well within ride-through).
        ac_voltage_ref = 240.0 if (drivers["grid_online"] or self.quattro.mode == "off-grid") \
            else 120.0
        fronius = self.fronius.step(dt, {
            "P_dc_available": pv["P_dc"],
            "V_grid_ac": ac_voltage_ref,
            "f_grid": 60.0,
            "P_ac_setpoint": 1.0,
        })
        dc = self.data_center.step(dt, {
            "IT_load_W": drivers["IT_load_kW"] * 1000.0,
            "ambient_temp_C": drivers["ambient_temp_C"],
            "hour": drivers["hour"],
            "workload_mix": drivers["workload_mix"],
        })
        chroma = self.chroma.step(dt, {"mode": "load",
                                        "P_command_W": float(drivers.get("chroma_load_kW", 0.0)) * 1000.0,
                                        "V_command": 240.0, "f_command": 60.0})
        grid_pre = self.grid.step(dt, {
            "online": drivers["grid_online"],
            "LMP": drivers["grid_LMP_usd_MWh"],
            "CI_gco2_kwh": drivers["grid_CO2_gco2_kwh"],
            "P_exchange_request_W": 0.0,
        })

        # 2. PLC decision based on current state
        plc_ctx = {
            "battery": self.battery.get_state(),
            "data_center": dc,
            "fronius": fronius,
            "grid": grid_pre,
            "policy": policy,
        }
        plc = self.plc.step(dt, plc_ctx)
        cmds = plc["commands"]

        # 3. Generator → DC-DC → battery DC bus
        gen = self.generator.step(dt, {"enable": cmds["generator_enable"],
                                        "P_request_W": cmds["generator_request_w"]})
        dcdc = self.dcdc.step(dt, {"enable": cmds["dcdc_enable"], "V_in": gen["V_dc"],
                                    "P_in_available_W": gen["P_dc"], "V_out_command": 51.2})
        mts = self.mts.step(dt, {"position_command": cmds["mts_position"], "manual_override": False})

        # 4. Quattro sets demanded battery flow
        quattro = self.quattro.step(dt, {
            "P_ac_setpoint": cmds["quattro_command_w"],
            "mode": cmds["quattro_mode"],
            "V_ac_grid": 120.0 if grid_pre["online"] else 0.0,
            "f_grid": 60.0,
        })
        # Battery: combine quattro DC draw and dcdc charging contribution
        # quattro P_dc convention: + draws from DC bus (=battery discharges); - pushes to battery
        bat_request = float(quattro["P_dc"]) - float(dcdc["P_out"])
        battery = self.battery.step(dt, {"P_bat_request_W": bat_request,
                                          "ambient_temp_C": drivers["ambient_temp_C"]})

        # Reconcile if battery couldn't deliver/absorb
        actual_bat_p = float(battery["P_dc"])
        achievable = actual_bat_p + float(dcdc["P_out"])
        if quattro["P_dc"] != 0:
            scale = max(0.0, min(1.0, abs(achievable) / max(abs(quattro["P_dc"]), 1.0)))
            quattro["P_ac"] *= scale
            quattro["P_dc"] *= scale
            self.quattro.state["P_ac"] = quattro["P_ac"]
            self.quattro.state["P_dc"] = quattro["P_dc"]

        cerbo = self.cerbo.step(dt, {"battery": battery, "grid": grid_pre, "quattro": quattro})

        # 5. AC panel power balance — quattro can supply (-P_ac) or sink (+P_ac)
        ac_supply = float(fronius["P_ac"]) + max(0.0, -float(quattro["P_ac"]))
        ac_sink_quattro = max(0.0, float(quattro["P_ac"]))  # charging
        ac_demand = float(dc["P_total"]) + max(0.0, float(chroma["P"])) + ac_sink_quattro
        grid_request = ac_demand - ac_supply  # >0 import, <0 export
        grid = self.grid.step(dt, {
            "online": drivers["grid_online"],
            "LMP": drivers["grid_LMP_usd_MWh"],
            "CI_gco2_kwh": drivers["grid_CO2_gco2_kwh"],
            "P_exchange_request_W": grid_request,
        })

        if grid["online"]:
            # On-grid: if requested import exceeds the import limit, the grid clips
            # `P_exchanged`, leaving an unmet AC deficit. Treat that as load shed
            # rather than a model error so the energy balance closes cleanly.
            unmet = ac_demand - (ac_supply + float(grid["P_exchanged"]))
            if unmet > 1.0:
                load_shed = unmet
                ac_demand -= unmet
                self.panel.faults = ["panel_load_shed_grid_limit"]
            else:
                load_shed = 0.0
            imbalance = ac_supply + float(grid["P_exchanged"]) - ac_demand
        else:
            # Off-grid: Quattro is the slack. If supply < demand, the difference is shed.
            # If supply > demand, the surplus is curtailed (Fronius freq-shift back-off).
            if ac_supply + 1.0 < ac_demand:
                load_shed = ac_demand - ac_supply
                ac_demand = ac_supply
                self.panel.faults = ["panel_load_shed_off_grid"]
            else:
                load_shed = 0.0
                if ac_supply > ac_demand + 1.0:
                    self.panel.faults = ["pv_curtailed_off_grid"]
                    ac_supply = ac_demand
            imbalance = ac_supply - ac_demand

        panel_branch_powers = {
            "data_center": float(dc["P_total"]),
            "grid_branch": abs(float(grid["P_exchanged"])) + max(0.0, float(chroma["P"])),
            "pv_branch": float(fronius["P_ac"]),
        }
        panel = self.panel.step(dt, {
            "voltage_v": 240.0 if (grid["online"] or quattro["mode"] == "off-grid") else 0.0,
            "branch_powers_w": panel_branch_powers,
        })

        records = self._records(ts)
        flows = [
            {"from": "pv_sim", "to": "fronius", "P_W": float(pv["P_dc"])},
            {"from": "fronius", "to": "panel", "P_W": float(fronius["P_ac"])},
            {"from": "generator", "to": "dcdc", "P_W": float(gen["P_dc"])},
            {"from": "dcdc", "to": "battery", "P_W": float(dcdc["P_out"])},
            {"from": "battery", "to": "quattro", "P_W": float(battery["P_dc"])},
            {"from": "quattro", "to": "panel", "P_W": -float(quattro["P_ac"])},
            {"from": "panel", "to": "data_center", "P_W": float(dc["P_total"])},
            {"from": "panel", "to": "chroma", "P_W": float(chroma["P"])},
            {"from": "grid", "to": "panel", "P_W": float(grid["P_exchanged"])},
        ]
        denom = max(ac_supply, ac_demand, 1.0)
        summary = {
            "components": {
                "pv_sim": pv, "fronius": fronius, "battery": battery,
                "quattro": quattro, "cerbo": cerbo, "dcdc": dcdc,
                "generator": gen, "mts": mts, "panel": panel,
                "chroma": chroma, "data_center": dc, "grid": grid, "plc": plc,
            },
            "flows": flows,
            "energy_balance_residual": abs(imbalance) / denom,
            "load_shed_w": load_shed,
            "ac_supply_w": ac_supply,
            "ac_demand_w": ac_demand,
        }
        return records, summary
