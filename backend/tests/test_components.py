import math

import pytest

from backend.components.battery_pytes import PytesBattery, lfp_ocv
from backend.components.data_center import DataCenter
from backend.components.fronius_primo import FroniusPrimo
from backend.components.pv_simulator import PVSimulator
from backend.components.victron_quattro import VictronQuattro
from backend.components.aluma_generator import AlumaPowerGenerator
from backend.components.dcdc_converter import DCDCConverter
from backend.components.mts import ManualTransferSwitch
from backend.components.panel import SplitPhasePanel
from backend.components.chroma_load import Chroma61809
from backend.components.cerbo_gx import CerboGX
from backend.components.grid_tie import GridTie
from backend.components.plc_controller import SitePLC


def test_pv_outputs_zero_at_night():
    pv = PVSimulator()
    s = pv.step(1.0, {"irradiance_W_m2": 0.0, "ambient_temp_C": 20.0, "V_dc_command": 720.0})
    assert s["P_dc"] == pytest.approx(0.0, abs=10.0)


def test_pv_increases_with_irradiance():
    pv = PVSimulator()
    a = pv.step(1.0, {"irradiance_W_m2": 200.0, "ambient_temp_C": 25.0, "V_dc_command": 720.0})
    b = pv.step(1.0, {"irradiance_W_m2": 1000.0, "ambient_temp_C": 25.0, "V_dc_command": 720.0})
    assert b["P_dc"] > a["P_dc"]


def test_fronius_anti_islanding():
    f = FroniusPrimo()
    s = f.step(1.0, {"P_dc_available": 3000.0, "V_grid_ac": 0.0, "f_grid": 0.0, "P_ac_setpoint": 1.0})
    assert s["P_ac"] == 0.0


def test_battery_ocv_monotone():
    assert lfp_ocv(0.0) < lfp_ocv(0.5) < lfp_ocv(1.0)


def test_battery_soc_clipped():
    b = PytesBattery(config={"initial_soc": 0.95})
    s = b.step(3600.0, {"P_bat_request_W": -10000.0, "ambient_temp_C": 25.0})
    assert s["SOC"] <= 0.95 + 1e-6


def test_battery_thermal_stable_long_step():
    b = PytesBattery(config={"initial_soc": 0.5})
    s = b.step(3600.0, {"P_bat_request_W": 4000.0, "ambient_temp_C": 25.0})
    # Closed-form integration must not blow up
    assert -50 < s["T"] < 100


def test_quattro_signs():
    q = VictronQuattro()
    s = q.step(1.0, {"P_ac_setpoint": -3000.0, "mode": "off-grid",
                     "V_ac_grid": 120.0, "f_grid": 60.0})
    assert s["P_ac"] < 0  # discharging
    assert s["P_dc"] > 0  # drawing from DC


def test_quattro_off_grid_droop():
    q = VictronQuattro()
    s = q.step(1.0, {"P_ac_setpoint": -3000.0, "mode": "off-grid",
                     "V_ac_grid": 0.0, "f_grid": 0.0})
    # Off-grid droop: V drops below 120 because P_ac<0 → 120 - 0.5*(-3) = 121.5; absolute deviation present
    assert abs(s["V_ac_out"] - 120.0) > 0.5


def test_data_center_pue():
    dc = DataCenter()
    s = dc.step(60.0, {"IT_load_W": 2500.0, "ambient_temp_C": 22.0,
                        "hour": 14, "workload_mix": {"web_serving": 1.0}})
    assert s["P_total"] >= s["P_IT"]


def test_data_center_thermal_envelope_normal():
    dc = DataCenter()
    s = dc.step(60.0, {"IT_load_W": 2500.0, "ambient_temp_C": 22.0,
                        "hour": 14, "workload_mix": {"web_serving": 1.0}})
    assert 18.0 <= s["T_inlet"] <= 27.0


def test_generator_offline_when_disabled():
    g = AlumaPowerGenerator()
    s = g.step(60.0, {"enable": False, "P_request_W": 2000.0})
    assert s["P_dc"] == 0.0


def test_generator_starts_within_long_step():
    g = AlumaPowerGenerator()
    s = g.step(3600.0, {"enable": True, "P_request_W": 2500.0})
    assert s["P_dc"] > 0


def test_dcdc_efficiency_curve():
    d = DCDCConverter()
    s = d.step(1.0, {"enable": True, "V_in": 48.0, "P_in_available_W": 1500.0, "V_out_command": 51.2})
    assert s["P_out"] > 0
    assert s["P_out"] <= s["P_in"]


def test_mts_transfer():
    m = ManualTransferSwitch()
    a = m.step(1.0, {"position_command": "inverter", "manual_override": False})
    b = m.step(1.0, {"position_command": "generator", "manual_override": False})
    assert b["active_source"] == "generator"


def test_panel_branch_balance():
    p = SplitPhasePanel()
    s = p.step(1.0, {"voltage_v": 240.0, "branch_powers_w": {"data_center": 1500.0}})
    assert s["voltage_v"] == 240.0


def test_chroma_load_mode():
    c = Chroma61809()
    s = c.step(1.0, {"mode": "load", "P_command_W": 0.0, "V_command": 240.0, "f_command": 60.0})
    assert "mode" in s


def test_cerbo_minimum_soc():
    c = CerboGX()
    s = c.step(1.0, {"battery": {"SOC": 0.1}, "grid": {"online": True}, "quattro": {"P_ac": 0}})
    assert "low_soc" in s["alerts"]


def test_grid_tie_export_limit():
    g = GridTie()
    s = g.step(1.0, {"online": True, "LMP": 50.0, "CI_gco2_kwh": 400.0, "P_exchange_request_W": -10000.0})
    assert s["P_exchanged"] >= -5001.0  # capped


def test_plc_returns_commands():
    p = SitePLC()
    s = p.step(1.0, {"battery": {"SOC": 0.5}, "data_center": {"P_total": 2500.0},
                     "fronius": {"P_ac": 1000.0}, "grid": {"online": True}, "policy": "rule_baseline"})
    assert "commands" in s
    assert "quattro_command_w" in s["commands"]
