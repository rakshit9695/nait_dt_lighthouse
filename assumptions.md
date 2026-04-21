# Assumptions Ledger

Until `Questions_for_NAIT.pdf` is supplied with concrete answers, the following defaults are used by the twin. All entries are tagged `assumed=true` in `backend/config/defaults.yaml`, and the frontend Inspect Panel surfaces them in italics.

| Q# | Parameter | Default | Unit | Notes |
|---:|-----------|--------:|------|-------|
| 1  | `dcdc.rated_power_w` | 2000 | W | Generic 48V buck-boost default per spec §2.2.6 |
| 2  | `generator.rated_power_w` | 3000 | W | AlumaPower LDES default per spec §2.2.7 |
| 3  | `generator.fuel_tank_kg` | 20 | kg | 24 kWh nameplate at 1.2 kWh/kg |
| 4  | `panel.branch_trip_a` | 30 | A | Spec default; 10 kA AIC, I²t inverse-time |
| 5  | `data_center.it_avg_kw` | 2.0 | kW | Spec default §2.2.11 |
| 6  | `data_center.it_peak_kw` | 3.5 | kW | Spec default §2.2.11 |
| 7  | `data_center.pue` | 1.6 | ratio | Spec default §2.2.11 |
| 8  | `grid.import_limit_w` | 10000 | W | Spec default §2.2.12 |
| 9  | `grid.export_limit_w` | 5000 | W | Spec default §2.2.12 |
| 10 | `mts.generator_path_is_dc_support` | true | bool | Brief mixes AC MTS with DC-only generator; modeled as DC-bus gate |
| 11 | `pv_sim.diode_ideality` | 1.4 | – | Single-diode fit; not in source SLD |
| 12 | `pv_sim.series_resistance_ohm` | 0.25 | Ω | String-level series resistance for I-V solver |
| 13 | `battery.thermal_capacity_j_per_k` | 4000 | J/K | Lumped m·c_p per spec §2.2.3 |
| 14 | `battery.thermal_conductance_w_per_k` | 2.0 | W/K | h per spec §2.2.3 |
| 15 | `mts.atg_transfer_time_s` | 0.1 | s | ATS mode transfer time per spec §2.2.8 |
