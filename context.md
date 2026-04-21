# NAIT CGI Microgrid Digital Twin — Contributor Context

This document is the **contributor onboarding brief** for the NAIT CGI Data
Center microgrid digital twin. It explains, end-to-end:

1. **System architecture** — what the codebase is and how the pieces fit.
2. **Component physics** — every device on the SLD, the equations it
   implements, and the conventions you must respect when touching it.
3. **The solver loop** — the exact order of operations inside one time step
   and why energy balance closes.
4. **Control policies** — the four dispatch strategies and their decision
   surfaces.
5. **Scenarios** — every canned scenario, what it stresses, the expected
   energy / power signature, and the verified backend numbers.
6. **Frontend abstraction layers (L1 → L2 → L3)** — what each layer surfaces
   to the operator, where the data comes from, and how to extend it.
7. **Evaluation engine** — how `DT_Confidence` is computed.
8. **Testing & deployment** — pytest, the stress harness, and the deployed
   stack.

If you only have time to read three sections, read **2 (Component physics)**,
**3 (Solver loop)**, and **5 (Scenarios)**. They contain the load-bearing
mental model.

---

## 1. System Architecture

```
scenarios/canned/*.yaml ──┐
backend/config/*.yaml ────┤
                          ▼
backend/components/*.py   (one model per SLD device)
            │
            ▼
backend/solver/network_solver.py   (orchestrates one time step)
            │
            ▼
backend/solver/simulator.py        (drives N steps, persists series)
            │
            ▼
backend/api/*.py                   (FastAPI: /api/v1/...,  /ws/live)
            │
            ▼
frontend/src/...                   (React/Vite SPA: SLD + L1/L2/L3)
            │
            ▼
backend/eval/scorer.py             (per-component C_i, system DT_Confidence)
```

Three coupled subsystems share one source of truth (the per-step component
state dict):

| Subsystem      | Role                                                                                              |
|----------------|---------------------------------------------------------------------------------------------------|
| **Backend**    | Time-stepping physics simulator + REST/WS API. Authoritative for all numbers.                     |
| **Eval**       | Per-component & system confidence scoring against reference curves.                               |
| **Frontend**   | React SPA: SLD canvas, scenario builder, story mode, three drill-through inspect layers.          |

### Code map

```
backend/
  components/   13 device models (one .py per SLD node)
  control/      4 dispatch policies (rule_baseline | economic | carbon_aware | external)
  solver/       network_solver.py (per-step), simulator.py (per-scenario)
  eval/         scorer.py, reference_data_loader.py, calibrate.py, report.py
  config/       defaults.yaml (parameters), topology.yaml (SLD), weights.yaml (DT_C weights)
  contracts.py  Pydantic schemas — the JSON contract with the frontend
  main.py       FastAPI app entrypoint
  tests/        pytest suite + stress_harness.py (large-N fuzz harness)

frontend/src/
  components/   SLDCanvas, InspectPanel, ScenarioBuilder, RunResultsPanel, ...
  components/internals/  L2 internal-state views per component type
  components/signals/    L3 governing-equation views per component type
  store.ts      Zustand store — single source of truth in the browser
  util/         icons, formatters, story order

scenarios/canned/*.yaml   8 canned scenarios with full driver time series
eval/                     generated run reports (HTML + JSON)
```

---

## 2. Component Physics

There are **13 components** wired together by `topology.yaml` (the SLD).
For each one below: convention, governing equation, and any subtle behaviour
contributors must preserve.

### 2.1 PV Simulator — Keysight N8937APV (`components/pv_simulator.py`)

* Implements a **single-diode PV model** with `brentq` root-finding for I(V).
* Scales `I_sc` linearly with irradiance `G/1000` and with cell temperature
  (`+0.05 %/°C`); shifts `V_oc` by `−0.30 %/°C` and `+0.06·ln(G_n)` for
  low-irradiance offset.
* Returns `P_dc = V·I` clipped to nameplate `15 kW`.
* Frontend reference curves (L3): IV family at 200/500/800/1000 W/m².

### 2.2 Fronius Primo 3.8-1 Inverter (`components/fronius_primo.py`)

* DC→AC, **unidirectional**. CEC-weighted efficiency curve via piecewise
  linear interpolation (peak 0.972 at 50 % loading).
* **Anti-islanding ride-through**:
  * `v_trip_t` accumulates dt while `|V_grid − 240| > 24 V` → trip after 1 s.
  * `f_trip_t` accumulates dt while `|f_grid − 60| > 0.5 Hz` → trip after
    0.16 s.
  * Trips set `status = "tripped"`, `P_ac = 0`, `faults = ["ride_through_trip"]`.
* **MPPT**: P&O on `V_dc_request` ±5 V, clamped 500–900 V.
* **Critical**: `dt = 3600 s` per step. A single step at the wrong AC voltage
  reference instantly trips the inverter. The solver passes `240 V` whenever
  grid OR Quattro-off-grid is up; otherwise `120 V` (which trips). See
  §3 step 1.

### 2.3 Pytes V5 LFP Battery (`components/battery_pytes.py`)

* **Pack**: 51.2 V nominal, 100 Ah, ~5.12 kWh.
* **OCV-SOC**: piecewise linear 44–54 V across 0–100 % SOC.
* **Equivalent circuit**: 1RC (`R0`, `R1·C1`) with closed-form RC dynamics so
  it is unconditionally stable at any `dt`.
* **SOC integration**: `SOC -= I·dt / (3600·Cap_Ah)`. Hard-clamped 10–95 %.
* **Convention**: `I > 0` = discharge (delivering to bus). `P_bat_request_W`
  follows the same sign.
* **Thermal**: first-order, closed form. `T_eq = T_amb + I²·(R0+R1)/h`,
  `T(t+dt) = T_eq + (T − T_eq)·exp(−dt/τ_th)`, `τ_th = mc_p/h`.
* **BMS clipping (`_bms_clip`)** — load-bearing safety:
  1. Hard limit `|I| ≤ I_max = 100 A`.
  2. Refuse discharge if SOC ≤ 10 %; refuse charge if SOC ≥ 95 %.
  3. **Thermal taper**: linear ramp to 0 between 45 °C and 50 °C, hard stop
     above 50 °C.
  4. **Thermal-feasibility cap**:
     `I_max,thermal = sqrt((48 − T_amb)·h/(R0+R1))`. Keeps steady-state
     `T_eq ≤ 48 °C` above ambient. At 48 °C ambient this forces `I = 0` —
     **this is correct safety behaviour**, not a bug.
* **SOH**: `1 − cycles_throughput·1e-5`, floored at 0.7.

### 2.4 Victron Quattro 48/5000/120V (`components/victron_quattro.py`)

* **Bidirectional** AC↔DC inverter, **slack bus** in off-grid mode.
* **Sign convention**: `P_ac_setpoint > 0` = charge battery (AC→DC),
  `< 0` = discharge (DC→AC). `P_dc` reflects the DC-side flow with the
  efficiency `η(load_fraction)` applied (charge: `P_dc = −P·η`; discharge:
  `P_dc = +P/η`).
* **No-load draw**: 25 W from DC bus when idle.
* **Off-grid droop**: `V_out = 120 − 0.5·(P_kW)`, `f_out = 60 − 0.02·(P_kW)`.
* **Mode switching**: 20 ms transition timer.

### 2.5 Cerbo GX (`components/cerbo_gx.py`)

* Read-only system aggregator. Emits `alerts` (e.g. `low_soc`,
  `battery:over_temperature`) and `ess_mode` (`support` | `island`).

### 2.6 DC-DC Converter (`components/dcdc_converter.py`)

* Generic 48 V buck-boost, 2 kW rated, 40 A out limit.
* Efficiency: 0.94 above 20 % load, linear taper down to 0.80.
* **Bidirectional source routing (set in `network_solver.step`)**:
  * Generator running → `gen → dcdc → battery` (charging).
  * Generator idle → `battery → dcdc → aux DC house load` (250 W aux).
  * The flow record direction and battery accounting flip accordingly so
    energy balance always closes. See §3 step 3.
* **Always enabled in `rule_baseline`** so the DC distribution path is
  always observable on the SLD.

### 2.7 AlumaPower Generator (`components/aluma_generator.py`)

* Aluminum-air fuel cell. **Polarization**: `V = V_OC − R·I − A·ln(I/I0) − M·exp(N·I)`,
  with `V_OC = 54 V`, `R = 0.08 Ω`. Solved by 8-iteration fixed-point.
* **Specific energy**: 1.2 kWh/kg of fuel.
* **States**: `off → starting (30 s) → running`. Ramp 200 W/s.
* **Daily exercise** (added 2026-04-21): when grid is online, `rule_baseline`
  enables a 1-hour run at 600 W at `hour_of_day == 3`. Mirrors real-world
  anti-wet-stacking practice and keeps the AlumaPower box on the SLD always
  showing meaningful values.
* `fuel_kg` decremented monotonically. When it hits 0 the unit refuses to
  start and emits `fuel_empty`.

### 2.8 Manual Transfer Switch (`components/mts.py`)

* Two positions: `inverter` (default) | `generator`. 0.1 s transfer time.
* Set to `generator` only when `rule_baseline` is in deep-outage mode
  (off-grid + SOC ≤ 20 %).

### 2.9 240/120V Split-Phase Panel (`components/panel.py`)

* Three branch breakers: `data_center`, `grid_branch`, `pv_branch`.
* **Inverse-time trip**: `t_trip = max(0.02, min(60, 0.18/((I/Itrip)² − 1)))`,
  `I_trip = 30 A`. Once tripped, stays tripped until `reset_breaker(branch)`
  is called.
* The solver sets `panel.faults = ["panel_load_shed_grid_limit"]` when the
  grid import limit clips, and `["pv_curtailed_off_grid"]` when off-grid PV
  surplus has nowhere to go.

### 2.10 Chroma 61809 (`components/chroma_load.py`)

* Programmable load / regen source. `mode = "load"` clamps to `0..9 kW`;
  `"source"` allows ±9 kW. Driven directly from
  `scenario.drivers.chroma_load_kW` (synthesized to ~0.7 kW baseline if
  absent).

### 2.11 Data Center (`components/data_center.py`)

* IT load + cooling. `P_total = P_IT + P_cool`, with PUE = 1.6.
* Cooling first-order ramp toward `(PUE−1)·P_IT` with α = `dt/180`.
* **ASHRAE envelope**: `T_inlet = 22 + 0.5·max(0, T_amb−30) + 0.0015·deficit`.
  Outside 18–27 °C → `ashrae_violation` fault.
* **Workload mix** drives a `flexibility` score (per-class shifting potential).

### 2.12 Grid Tie (`components/grid_tie.py`)

* Convention: `P_exchanged > 0` = importing.
* Limits: `import = 10 kW`, `export = 5 kW`. The solver enforces these and
  **books overflow as load shed** rather than letting it leak into the
  energy-balance residual.
* Carries `LMP [USD/MWh]` and `CI [gCO₂/kWh]` for the carbon/economic
  policies.

### 2.13 Site PLC (`components/plc_controller.py`)

* Wraps the policy registry in `control/policies.py`. Calls the active
  handler with the full `plc_ctx` dict and stores the resulting `commands`
  for one tick. Forwards every command field verbatim — if you add a new
  command, also add it to the policy output and to the solver consumer.

---

## 3. Solver Loop — `network_solver.NetworkSolver.step()`

One physics tick proceeds in a strict order. Cross-section coupling is done
by **two passes** of the grid model so the AC bus closes:

```
1. Sources / drivers
   1a. PV  ← (irradiance, T_amb) → P_dc
   1b. ac_voltage_ref = 240 V if (grid_online OR quattro.mode == "off-grid") else 120 V
       Fronius ← (P_dc, V_grid_ac=ac_voltage_ref, f_grid)  → P_ac, MPPT, ride-through
   1c. DataCenter ← (IT_load, ambient, hour, mix) → P_total
   1d. Chroma ← driver kW
   1e. Grid (pre-pass) ← (online, LMP, CI, P_request=0)

2. PLC decision
   plc_ctx = { battery, data_center, fronius, grid, generator, hour_of_day, policy }
   cmds = POLICIES[plc_ctx.policy](plc_ctx)

3. Generator → DC-DC → Battery DC bus
   gen ← (enable, P_request_W) → P_dc, V_dc, fuel
   dcdc_from_battery = (gen.P_dc < 50W AND cmds.dcdc_enable AND cmds.dc_aux_load_w > 0)
   if dcdc_from_battery:
       dcdc ← (enable, V_in=51.2, P_in_available=dc_aux_load_w, V_out_command=51.2)
   else:
       dcdc ← (enable, V_in=gen.V_dc, P_in_available=gen.P_dc, V_out_command=51.2)
   mts ← (position_command)

4. Quattro (sets demanded battery flow)
   quattro ← (P_ac_setpoint, mode, V_ac_grid, f_grid) → P_ac, P_dc

   Battery request:
     if dcdc_from_battery:  bat_request = quattro.P_dc + dcdc.P_in   (battery sources DCDC)
     else:                  bat_request = quattro.P_dc - dcdc.P_out  (DCDC charges battery)
   battery ← (P_bat_request_W, ambient_temp_C) → actual P_dc

   Reconcile: if battery couldn't deliver/absorb the requested P_dc, scale
   quattro.P_ac and quattro.P_dc proportionally so AC commitments are honest.

   cerbo ← (battery, grid, quattro)

5. AC panel balance + grid (final pass)
   ac_supply = fronius.P_ac + max(0, -quattro.P_ac)        (PV + Quattro discharge)
   ac_sink   = max(0, +quattro.P_ac)                       (Quattro charging)
   ac_demand = data_center.P_total + max(0, chroma.P) + ac_sink
   grid_request = ac_demand − ac_supply                    (>0 import, <0 export)
   grid ← (online, LMP, CI, P_exchange_request=grid_request)

   if grid.online:
       unmet = ac_demand − (ac_supply + grid.P_exchanged)
       if unmet > 1 W: load_shed = unmet; ac_demand -= unmet
                       panel.faults = ["panel_load_shed_grid_limit"]
       imbalance = ac_supply + grid.P_exchanged − ac_demand
   else:
       if ac_supply + 1 < ac_demand:
           load_shed = ac_demand − ac_supply; ac_demand = ac_supply
           panel.faults = ["panel_load_shed_off_grid"]
       elif ac_supply > ac_demand + 1:
           panel.faults = ["pv_curtailed_off_grid"]
           ac_supply = ac_demand
       imbalance = ac_supply − ac_demand                   (≈0 by construction)

   panel ← (voltage, branch_powers)

6. Emit records, flow list, summary {energy_balance_residual, load_shed_w, ...}
```

**Conventions you must not change without updating every consumer:**

* **All powers in Watts**, all energies in Wh, all times in seconds.
* **Battery I sign**: `+I` = discharge.
* **Quattro P_ac sign**: `+` = charging from AC, `−` = discharging to AC.
* **Grid P_exchanged sign**: `+` = import.
* **Flow records** are directional (`from → to`) and the magnitude is signed
  in the listed direction. The frontend takes `|P_W|` for visualisation but
  the sign is preserved for diagnostics.

---

## 4. Control Policies (`backend/control/`)

Every policy receives the same `plc_ctx` dict and must return a `cmds` dict
with the keys consumed by `network_solver`:
`fronius_setpoint_pct, quattro_mode, quattro_command_w, generator_enable,
generator_request_w, dcdc_enable, dc_aux_load_w (optional), mts_position,
chroma_mode, chroma_power_w`.

### 4.1 `rule_baseline` (default for most scenarios)

* **Off-grid**:
  * SOC > 20 % → Quattro discharges to cover the deficit (≤ 4.5 kW).
  * SOC ≤ 20 % → start generator (1–3 kW), close MTS to generator path,
    Quattro picks up the residual.
* **Grid-tied**:
  * Surplus > 100 W and SOC < 95 % → charge (taper above SOC 50 %).
  * Deficit > 100 W and SOC > 25 % → discharge (taper below SOC 70 %).
  * `hour_of_day == 3` → daily generator exercise at 600 W (1 h).
  * DC-DC always enabled with a 250 W aux DC house load — battery sources
    it whenever generator is idle.

### 4.2 `economic` (single-step LP via `pulp.PULP_CBC_CMD`)

Minimises `LMP·import − 0.8·LMP·export + 20·(charge+discharge)/1000` subject
to `pv + bd + gi == load + bc + ge`. Forbids discharge below SOC 15 %,
charge above SOC 90 %.

### 4.3 `carbon_aware`

* `CI > 550` and SOC > 35 % → discharge ≤ 3.5 kW (avoid dirty grid).
* `CI < 350` and SOC < 85 % → charge ≤ 2.5 kW (bank clean grid).
* Off-grid mirrors `rule_baseline` deep-outage path.

### 4.4 `external`

Reads commands from a hook (e.g. an external optimiser) — see
`control/external_hook.py`. Useful for plugging in a co-simulation.

---

## 5. Scenarios

All canned scenarios live in `scenarios/canned/*.yaml`. They share the same
schema (`contracts.Scenario`): hourly drivers (`irradiance_W_m2`,
`ambient_temp_C`, `grid_LMP_usd_MWh`, `grid_CO2_gco2_kwh`, `IT_load_kW`,
`grid_online`, `workload_mix`, optional `chroma_load_kW`), an
`initial_state` (`battery_SOC`, `fuel_kg`, `grid_online`), and a
`control_policy`.

The numbers in each scenario card below come from a clean run on
2026-04-21 (post DC-DC always-on + generator exercise fixes). Format:
`peak / mean (nonzero_steps/total_steps)`. All energies positive.

### 5.1 `sunny_grid_stable` (72 h, `rule_baseline`)

The default "happy path". Strong solar bell-curve every day, stable grid.

**Stresses**: the daily PV/load reconciliation; serves as the regression
baseline for everything else.

| Component        | Peak       | Mean      | Notes                                    |
|------------------|------------|-----------|------------------------------------------|
| PV (DC)          | 4 974 W    | 1 422 W   | 12 noon every day                        |
| Fronius (AC)     | 3 800 W    | 1 303 W   | Clipped to nameplate at solar noon       |
| Grid import      | 5 796 W    | 3 410 W   | Carries baseline load most of the time   |
| Battery P_dc     | 2 001 W    | 32 W      | Discharges briefly when PV dips          |
| Quattro AC       | −1 667 W   | −13 W     | Mostly idle (no big surplus or deficit)  |
| **Generator**    | 600 W      | 25 W      | Daily 1 h exercise (3/72 steps)          |
| **DC-DC**        | 564 W      | 236 W     | Aux house load every step (72/72)        |
| Data Center      | 4 800 W    | 4 000 W   | 2.5 kW IT × PUE 1.6                      |
| Chroma           | 1 000 W    | 725 W     | Aux research load                        |
| **DT_Confidence**| **0.832**  |           | Best in the canned set                   |

### 5.2 `cloudy_grid_stable` (48 h, `rule_baseline`)

Heavy cloud cover: PV peaks ~1.6 kW (vs 5 kW sunny). Grid carries the
shortfall.

| Component | Peak | Mean | Notes |
|---|---:|---:|---|
| PV (DC) | 1 630 W | 473 W | Capped by irradiance |
| Fronius | 1 584 W | 457 W | |
| Grid import | 5 796 W | 4 233 W | ~25 % higher than sunny |
| Battery | 2 001 W | 45 W | Brief discharge cycles |
| Generator | 600 W | 25 W | Daily exercise |
| DC-DC | 564 W | 236 W | Aux load |
| **DT_C** | **0.832** | | |

### 5.3 `grid_outage_noon` (48 h, `rule_baseline`)

Grid drops at hour 12 (peak PV) and stays out until end-of-horizon. Tests
**black-start to islanded operation** and the generator deep-outage path.

| Component | Peak | Mean | Notes |
|---|---:|---:|---|
| PV (DC) | 4 628 W | 1 337 W | Carries the day, curtailed by Fronius freq-shift when in surplus |
| Fronius | 3 800 W | 1 182 W | One step (47/48) at zero — outage transient |
| Quattro | −1 667 W | −55 W | Forms 240 V split-phase off-grid |
| Battery | 2 001 W | 53 W | Deep discharge during outage |
| **Generator** | 3 000 W | 88 W | Real outage start (3 nonzero steps) |
| **DC-DC** | 1 880 W | 271 W | Now relays gen→battery, peaks higher |
| Grid (when up) | 5 797 W | 3 345 W | |
| Panel faults | | | `pv_curtailed_off_grid` flagged when surplus has no sink |
| **DT_C** | **0.832** | | |

### 5.4 `heatwave` (48 h, `rule_baseline`)

Sustained 42 °C ambient. Tests battery thermal model and ASHRAE envelope.

| Component | Peak | Mean | Notes |
|---|---:|---:|---|
| Battery T | **44.2 °C** | 38.2 °C | Stays under 50 °C cutoff thanks to thermal-feasibility cap |
| Battery P_dc | 1 261 W | 48 W | Reduced from 2 kW peak — thermal cap is biting |
| Quattro | −1 140 W | −20 W | Discharge throttled (battery limited) |
| PV | 4 280 W | 1 202 W | Slight derate from cell temp |
| Generator | 600 W | 25 W | Exercise |
| DC-DC | 564 W | 236 W | Aux |
| **DT_C** | **0.830** | | Battery scoring penalty for elevated T |

**Key insight**: this scenario is the regression test for the
`_bms_clip` thermal-feasibility cap. If battery T ever exceeds 50 °C here,
the cap is broken.

### 5.5 `price_spike_evening` (48 h, `economic`)

LMP spikes 5–10× during evening peak (hours 17–21). Economic LP discharges
hard during the spike, recharges off-peak.

| Component | Peak | Mean | Notes |
|---|---:|---:|---|
| Battery | 2 331 W | 163 W | **All 48 steps active** — LP cycles aggressively |
| Quattro | −2 144 W | −171 W | Highest discharge of any canned scenario |
| Battery T | 44.3 °C | 24.2 °C | Cycling-induced heat |
| Generator | 0 | 0 | Economic policy has no exercise schedule |
| DC-DC | 0 | 0 | Same — only used by `rule_baseline` aux path |
| Grid | 5 796 W | 4 097 W | Heavy import during off-peak |
| **DT_C** | **0.811** | | LP makes "noisier" decisions, lower physical_consistency |

> Note: `economic` and `carbon_aware` policies do not emit
> `dc_aux_load_w` and disable DC-DC by default. Generator + DCDC will read 0
> in those scenarios. This is **policy behaviour**, not a bug — the box
> still reports ride-through-ready state on L1.

### 5.6 `carbon_high_night` (48 h, `carbon_aware`)

Overnight CO₂ intensity is high (coal-heavy generation). Carbon-aware
policy charges by day (clean) and discharges by night (dirty grid).

| Component | Peak | Mean | Notes |
|---|---:|---:|---|
| Battery | 2 121 W | 35 W | Highest nonzero coverage (46/48) |
| Battery SOC | **0.92** | 0.51 | Fully cycles SOC 30 % ↔ 90 % |
| Battery T | 47.4 °C | 24.7 °C | Highest in canned set; **just under** the cap |
| Quattro | −1 947 W | −11 W | Big discharges at night |
| Generator/DCDC | 0/0 | 0/0 | Carbon-aware doesn't use them on grid |
| **DT_C** | **0.811** | | |

### 5.7 `ai_training_burst` (48 h, `rule_baseline`)

IT load surges to 5.6 kW (3.5 kW peak IT × PUE 1.6) during training windows.

| Component | Peak | Mean | Notes |
|---|---:|---:|---|
| Data Center | **5 600 W** | 3 600 W | Peaks above sunny baseline |
| PV / Fronius | 4 658 / 3 800 W | 1 347 / 1 264 W | Same solar profile |
| Battery | 1 667 W | 47 W | Smooths burst transitions |
| Grid | 5 646 W | 3 033 W | Imports more during bursts |
| Generator | 600 W | 25 W | Exercise |
| DC-DC | 564 W | 236 W | Aux |
| **DT_C** | **0.832** | | |

### 5.8 `worst_case` (48 h, `rule_baseline`, init SOC 0.35, fuel 15 kg)

Combined heatwave + grid outage windows + price spike + AI burst. The
hardest canned scenario.

| Component | Peak | Mean | Notes |
|---|---:|---:|---|
| Battery T | **47.8 °C** | 40.0 °C | Highest in canned set; thermal cap engaged |
| Battery | 1 637 W | 66 W | Cap-limited |
| Quattro | −1 488 W | −168 W | Heavy continuous discharge |
| **Generator** | 2 400 W | 325 W | 8 nonzero steps — real outage runs |
| **DC-DC** | 1 880 W | 443 W | Relays gen + aux house |
| Grid (when up) | 6 319 W | 3 204 W | Hits the 10 kW import limit occasionally |
| Data Center | 5 600 W | 3 600 W | Burst load |
| PV | 1 485 W | 420 W | Cloud + heat derate |
| **DT_C** | **0.824** | | Lower from faults/load-shed events |

---

## 6. Frontend Abstraction Layers

The frontend (`frontend/src`) renders a **Single-Line Diagram** (SLD) and a
right-hand **Inspect Panel** with three drill-through layers when a node is
selected. Layer captions live in `InspectPanel.tsx`.

### Layer 1 — Live Snapshot (component-level operator view)

* **Source**: the latest tick written to the Zustand store
  (`store.components[id].state`). On a deployed run with no live WebSocket,
  this is the **last step of the most recent `runResult`** (the SLD also
  shows per-edge `peak |P|` from `runResult.flowsPerStep` so intermittently
  active components like Quattro / Generator / DC-DC are not misleading;
  the "pk" suffix appears whenever peak > |live|).
* **Renders**: every key/value of the component's state dict, faults, and
  current assumptions. This is what an operator looking at SCADA would see.

### Layer 2 — Internal Model State (engineering view)

* **Source**: same component state, but rearranged into the **internal
  dynamics** of the model (e.g. for the battery: SOC, V_RC, T, cycle
  throughput, BMS clip flags; for the inverter: ride-through timers,
  efficiency point on the CEC curve; for the generator: state machine
  position + ramp).
* **Files**: `components/internals/BatteryInternals.tsx`,
  `components/internals/GenericInternals.tsx`. Add new internals views per
  type when warranted.

### Layer 3 — Governing Equations (physics view)

* **Source**: stitched from the component's state plus its
  `reference_curves()` output (e.g. PV IV-family, Fronius CEC curve,
  battery OCV-SOC).
* **Renders**: the actual equation(s) the model integrates with the
  **current** numeric values substituted, plus a sparkline / chart of the
  governing curve. This is the layer to look at when validating
  twin-vs-physics correctness.
* **Files**: `components/signals/{Battery,Inverter,PV}Signals.tsx`.

### Other panels

* **`SLDCanvas.tsx`** — draws the topology with live edge widths and per-node
  power readouts. Uses `displayFlows` memo to surface peak power across the
  current run when one is loaded.
* **`ScenarioBuilder.tsx`** — hourly driver editor + run trigger. POSTs to
  `/api/v1/scenarios/{id}/run`.
* **`StoryControls.tsx` + `StoryMetricsPanel.tsx`** — narrated walkthrough
  of a completed run, one component at a time, with cumulative kWh
  metrics.
* **`RunResultsPanel.tsx`** — DT_Confidence breakdown, fault timeline,
  energy summary.

### Store (`frontend/src/store.ts`)

Single zustand store. Key slices:

* `components` (per-id snapshot), `flows` (latest), `topology` (nodes/edges).
* `runResult` — set on completion; drives L2/L3 historical charts and the
  SLD peak-power overlay.
* `setLive(frame)` — WebSocket tick handler; overwrites `components` +
  `flows` per frame.

---

## 7. Evaluation — DT_Confidence (`backend/eval/scorer.py`)

Per-component score:
`C_i = w1·physical_consistency + w2·empirical_match + w3·assumption_density`

Defaults (`config/weights.yaml`): `w1 = 0.50, w2 = 0.35, w3 = 0.15`.

* **physical_consistency** — fault penalty (−0.05/fault), hard zero on SOC
  out of bounds or battery T > 60 °C, and a residual penalty
  `−min(0.3, 2·energy_balance_residual)`.
* **empirical_match** — observed vs reference for one canonical state field
  per component, scaled by tolerance (defined in
  `eval/reference_data_loader.REFERENCE_TARGETS`).
* **assumption_density** — `1 − (n_assumed / n_total_params)`. Forces
  contributors to lock down assumptions (see `assumptions.md` and the
  `assumed: true` flags in `config/defaults.yaml`).

System-level **`DT_Confidence` = harmonic mean** of all `C_i`. The harmonic
mean punishes any one weak component, so improving the worst component
buys more than improving the strongest.

Acceptance gates currently in use:

* Pytest suite: 32 tests must pass.
* Stress harness (`backend/tests/stress_harness.py`):
  canned + edge `DT_C ≥ 0.80`, fuzz `DT_C ≥ 0.70`, mean energy residual
  `< 0.5 %`, no NaN/Inf, SOC ∈ [0.10, 0.95], battery T < 60 °C, fuel
  monotonic, every canned scenario must produce `|Quattro.P_ac| > 50 W`
  somewhere.

---

## 8. Testing & Deployment

### Local

```powershell
# Backend
python -m venv .venv ; .\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
uvicorn backend.main:app --reload    # http://localhost:8000

# Frontend
cd frontend ; npm install ; npm run dev   # http://localhost:5173

# Tests
pytest --cov=backend --cov-report=term-missing
python -m backend.tests.stress_harness 200      # 8 canned + 10 edge + 200 fuzz
```

### Stress harness

Single source of truth for backend physics correctness. Run it any time
you touch a `components/*.py`, `solver/*.py`, or `control/*.py` file. A
clean run looks like:

```
=== Canned scenarios ===   (8 passes, q_peak 1.1–2.1 kW each, residuals ≈ 0)
=== Edge cases ===         (10 passes, dt_conf 0.83+)
=== N fuzz scenarios ===   (0 fatals, 0 errors)
=== Issue ledger ===       only the 2 expected WARNs
                            (battery refuses cycling at 48 °C ambient,
                             chroma idle when commanded 0)
```

If the ledger ever shows a new pattern, treat it as a regression and
diagnose before merging.

### Deployment

* **Backend** → Render (`render.yaml`, Docker). Auto-deploys on push to
  `main`. Free tier sleeps after 15 min; cold start ~30 s.
  Production base: `https://nait-dt-backend.onrender.com`.
* **Frontend** → Vercel, root `frontend/`. Auto-deploys on push.
  `VITE_API_BASE_URL` points at the Render service.
* **Auth**: bearer token via `NAIT_DT_TOKEN` env var (default `dev-token`
  in local dev).

---

## 9. Conventions Cheat-Sheet

* All powers in **W**, all energies in **Wh**, all times in **seconds**.
* Battery `I > 0` = discharge. SOC ∈ [0.10, 0.95] hard-clamped.
* Quattro `P_ac > 0` = charging from AC. Off-grid mode is the AC slack.
* Grid `P_exchanged > 0` = importing. Limits enforced and overage booked
  as `load_shed`, never as energy-balance error.
* Fronius **must** see a 240 V reference whenever any AC source is up
  (grid OR Quattro off-grid). One step at the wrong V trips it.
* Energy-balance residual is reported per step in `summary["energy_balance_residual"]`.
  Mean across a scenario should be `< 0.5 %`.
* Add a new component → add the model, register it in
  `network_solver.NetworkSolver.__init__`, add a node in
  `config/topology.yaml`, add a Pydantic literal to `contracts.ComponentType`,
  expose a reference curve, and (if dispatchable) add the command field to
  every policy.
* Add a new policy → register in `control/policies.POLICIES`, mirror the
  full command schema (don't drop fields — the solver will read default
  zeros and silently disable behaviour).
* Add a new scenario → drop a YAML in `scenarios/canned/`, ensure all
  driver arrays match `horizon_hours` length. Run the stress harness; it
  will pick it up automatically.
