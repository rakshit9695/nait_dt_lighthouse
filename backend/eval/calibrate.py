"""Calibration CLI stub (spec §4.6).

Usage:
    python -m backend.eval.calibrate --component battery --dataset epri_lfp_2022.parquet
"""
from __future__ import annotations

import argparse
from pathlib import Path


def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--component", required=True)
    p.add_argument("--dataset", required=True)
    args = p.parse_args()
    src = Path(args.dataset)
    if not src.exists():
        print(f"Dataset not found: {src}; calibration scaffold accepted (no-op).")
        return 0
    print(f"Calibrating component={args.component} against {src}")
    # Real implementation would do least-squares fit and bump version counter.
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
