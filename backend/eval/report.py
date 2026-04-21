"""HTML + JSON report rendering (spec §4.5)."""
from __future__ import annotations

from pathlib import Path

from jinja2 import Template

from backend.contracts import EvaluationReport


_TPL = Template("""<!doctype html>
<html lang="en"><head><meta charset="utf-8"/>
<title>NAIT CGI DT Report — {{ r.run_id }}</title>
<style>
  body { font-family: ui-sans-serif, system-ui, sans-serif; background:#fafafa; color:#111; margin:24px; }
  table { border-collapse: collapse; width:100%; margin-bottom:24px; }
  th,td { border:1px solid #ddd; padding:6px 8px; font-size:13px; text-align:left; }
  th { background:#f0f0f0; }
  .tile { border:2px solid #111; padding:18px 26px; display:inline-block; font-size:34px; margin:0 0 24px 0; font-family: ui-monospace, monospace; }
  h2 { margin-top: 32px; font-size:14px; text-transform:uppercase; letter-spacing:0.05em; }
  .muted { color:#666; font-size:12px; }
</style></head>
<body>
  <div class="tile">DT Confidence: {{ "%.3f"|format(r.dt_confidence) }}</div>
  <div class="muted">Run {{ r.run_id }} · Scenario {{ r.scenario_id }} · Generated {{ r.generated_at }}</div>

  <h2>System metrics</h2>
  <table><tbody>
  {% for k, v in r.system_metrics.items() %}
    <tr><th>{{ k }}</th><td>{{ "%.4f"|format(v) if v is number else v }}</td></tr>
  {% endfor %}
  </tbody></table>

  <h2>Per-component confidence</h2>
  <table>
    <thead><tr><th>id</th><th>C_i</th><th>physical</th><th>empirical</th><th>assumption density</th><th>faults</th></tr></thead>
    <tbody>
    {% for c in r.components %}
      <tr>
        <td>{{ c.id }}</td>
        <td>{{ "%.3f"|format(c.C_i) }}</td>
        <td>{{ "%.3f"|format(c.physical_consistency) }}</td>
        <td>{{ "%.3f"|format(c.empirical_match) }}</td>
        <td>{{ "%.3f"|format(c.assumption_density) }}</td>
        <td>{{ c.details.faults | join(', ') }}</td>
      </tr>
    {% endfor %}
    </tbody>
  </table>
</body></html>
""")


def write_report(report: EvaluationReport, out_dir: Path) -> tuple[Path, Path]:
    out_dir.mkdir(parents=True, exist_ok=True)
    json_p = out_dir / f"run_{report.run_id}.json"
    html_p = out_dir / f"run_{report.run_id}.html"
    json_p.write_text(report.model_dump_json(indent=2), encoding="utf-8")
    html_p.write_text(_TPL.render(r=report.model_dump(mode="json")), encoding="utf-8")
    return json_p, html_p
