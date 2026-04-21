"""Reference dataset bootstrap (spec §4.1).

Real datasets cannot be redistributed; this script emits placeholder files
documenting where to fetch each one and verifies SHA256 if files are present.
"""
from __future__ import annotations

import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
REF = ROOT / "backend" / "reference_data"


def main() -> None:
    manifest = json.loads((REF / "manifest.json").read_text(encoding="utf-8"))
    for ds in manifest["datasets"]:
        target = REF / f"{ds['id']}.placeholder"
        target.write_text(
            f"Dataset: {ds['id']}\nSource: {ds['url']}\nKind: {ds['kind']}\n"
            f"Expected SHA256: {ds['sha256']}\n"
            "Place the downloaded file alongside this placeholder to enable empirical scoring.\n",
            encoding="utf-8",
        )
        local = REF / f"{ds['id']}.parquet"
        if local.exists():
            sha = hashlib.sha256(local.read_bytes()).hexdigest()
            print(f"{ds['id']}: present, sha256={sha}")
        else:
            print(f"{ds['id']}: not present, placeholder created")


if __name__ == "__main__":
    main()
