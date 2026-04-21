from backend.solver.simulator import SIMULATOR
from backend.solver.safety import clip_command


def test_safety_clips_battery_soc():
    out, vios = clip_command("battery", {"SOC": 0.99})
    assert out["SOC"] == 0.95
    assert "battery.SOC" in vios


def test_safety_clips_quattro_power():
    out, vios = clip_command("quattro", {"power_w": 8000})
    assert out["power_w"] == 5000
    assert "quattro.power_w" in vios


def test_safety_passthrough_when_in_envelope():
    out, vios = clip_command("battery", {"SOC": 0.5})
    assert vios == []
    assert out["SOC"] == 0.5


def test_sunny_scenario_meets_acceptance():
    summary = SIMULATOR.run_scenario("sunny_grid_stable")
    assert summary.evaluation.dt_confidence >= 0.80
    assert summary.evaluation.system_metrics["energy_balance_residual"] < 0.005


def test_all_canned_scenarios_meet_dt_confidence():
    for sid in ["cloudy_grid_stable", "grid_outage_noon", "price_spike_evening",
                "carbon_high_night", "heatwave", "ai_training_burst", "worst_case"]:
        summary = SIMULATOR.run_scenario(sid)
        assert summary.evaluation.dt_confidence >= 0.80, f"{sid} below 0.80"


def test_evaluation_report_round_trip():
    s = SIMULATOR.run_scenario("sunny_grid_stable")
    j = s.evaluation.model_dump_json()
    assert "dt_confidence" in j
    assert s.evaluation.run_id in j
