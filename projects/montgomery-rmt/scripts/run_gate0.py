#!/usr/bin/env python3
"""Run Montgomery-RMT Gate 0 end to end."""

from __future__ import annotations

import argparse
import csv
import datetime as dt
import hashlib
import json
import platform
import subprocess
import sys
from pathlib import Path

import numpy as np


PROJECT = Path(__file__).resolve().parents[1]
SCRIPTS = PROJECT / "scripts"
PROCESSED = PROJECT / "data" / "processed"
OUTPUTS = PROJECT / "outputs"


def utc_now() -> str:
    return dt.datetime.now(dt.UTC).replace(microsecond=0).isoformat()


def run(command: list[str]) -> None:
    print("==>", " ".join(command))
    subprocess.run(command, cwd=PROJECT, check=True)


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def project_files() -> list[Path]:
    files: list[Path] = []
    for subdir in [PROJECT / "data" / "raw", PROJECT / "data" / "processed", OUTPUTS]:
        if subdir.exists():
            files.extend(path for path in subdir.rglob("*") if path.is_file())
    return sorted(
        path
        for path in files
        if path != OUTPUTS / "hashes.json" and path.name != ".gitkeep"
    )


def write_hashes() -> dict[str, str]:
    hashes = {str(path.relative_to(PROJECT)): sha256(path) for path in project_files()}
    (OUTPUTS / "hashes.json").write_text(json.dumps(hashes, indent=2, sort_keys=True) + "\n")
    return hashes


def read_spacing_mean(path: Path) -> tuple[int, float]:
    values: list[float] = []
    with path.open(newline="") as handle:
        reader = csv.DictReader(handle)
        for row in reader:
            column = "spacing_normalized"
            try:
                values.append(float(row[column]))
            except (KeyError, TypeError, ValueError):
                continue
    if not values:
        return 0, float("nan")
    arr = np.array(values, dtype=float)
    return len(values), float(arr.mean())


def l2_distance(path: Path) -> float:
    values: list[tuple[float, float]] = []
    with path.open(newline="") as handle:
        reader = csv.DictReader(handle)
        for row in reader:
            values.append((float(row["density"]), float(row["sine_kernel"])))
    arr = np.array(values, dtype=float)
    return float(np.sqrt(np.mean((arr[:, 0] - arr[:, 1]) ** 2)))


def load_manifest() -> dict[str, object]:
    path = PROJECT / "data" / "manifest.json"
    return json.loads(path.read_text()) if path.exists() else {}


def write_metrics(args: argparse.Namespace) -> None:
    manifest = load_manifest()
    zeta_count, zeta_mean = read_spacing_mean(PROCESSED / "zeta_spacings.csv")
    gue_count, gue_mean = read_spacing_mean(PROCESSED / "gue_spacings.csv")
    goe_count, goe_mean = read_spacing_mean(PROCESSED / "goe_spacings.csv")
    poisson_count, poisson_mean = read_spacing_mean(PROCESSED / "poisson_spacings.csv")
    metrics = {
        "generated_at_utc": utc_now(),
        "python_version": sys.version,
        "platform": platform.platform(),
        "seeds": {"rmt": args.rmt_seed, "poisson": args.poisson_seed},
        "zeta_source": manifest.get("source"),
        "zeta_zero_count": manifest.get("actual_n"),
        "spacing_count": zeta_count,
        "histogram_parameters": {
            "u_max": args.u_max,
            "bin_width": args.bin_width,
            "max_k": args.max_k,
        },
        "rmt_matrix_size": args.matrix_size,
        "rmt_sample_count": args.samples,
        "poisson_sample_count": args.poisson_n,
        "mean_normalized_spacing": {
            "zeta": zeta_mean,
            "gue": gue_mean,
            "goe": goe_mean,
            "poisson": poisson_mean,
        },
        "spacing_counts": {
            "zeta": zeta_count,
            "gue": gue_count,
            "goe": goe_count,
            "poisson": poisson_count,
        },
        "l2_distance_to_sine_kernel": {
            "zeta": l2_distance(PROCESSED / "zeta_paircorr.csv"),
            "gue": l2_distance(PROCESSED / "gue_paircorr.csv"),
            "goe": l2_distance(PROCESSED / "goe_paircorr.csv"),
            "poisson": l2_distance(PROCESSED / "poisson_paircorr.csv"),
        },
    }
    OUTPUTS.mkdir(parents=True, exist_ok=True)
    (OUTPUTS / "metrics.json").write_text(json.dumps(metrics, indent=2, sort_keys=True) + "\n")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--n", type=int, default=10000)
    parser.add_argument("--fallback-n", type=int, default=1000)
    parser.add_argument("--sage-timeout", type=int, default=60)
    parser.add_argument("--u-max", type=float, default=5.0)
    parser.add_argument("--bin-width", type=float, default=0.05)
    parser.add_argument("--max-k", type=int, default=50)
    parser.add_argument("--matrix-size", type=int, default=80)
    parser.add_argument("--samples", type=int, default=25)
    parser.add_argument("--bulk-frac", type=float, default=0.6)
    parser.add_argument("--rmt-seed", type=int, default=1729)
    parser.add_argument("--poisson-n", type=int, default=10000)
    parser.add_argument("--poisson-seed", type=int, default=314159)
    args = parser.parse_args()

    py = sys.executable
    run([py, str(SCRIPTS / "fetch_odlyzko.py"), "--n", str(args.n), "--fallback-n", str(args.fallback_n), "--sage-timeout", str(args.sage_timeout)])
    run([py, str(SCRIPTS / "zeta_spacing.py")])
    run([py, str(SCRIPTS / "paircorr.py"), "--u-max", str(args.u_max), "--bin-width", str(args.bin_width), "--max-k", str(args.max_k)])
    run([
        py,
        str(SCRIPTS / "simulate_rmt.py"),
        "--ensemble",
        "both",
        "--matrix-size",
        str(args.matrix_size),
        "--samples",
        str(args.samples),
        "--bulk-frac",
        str(args.bulk_frac),
        "--seed",
        str(args.rmt_seed),
        "--u-max",
        str(args.u_max),
        "--bin-width",
        str(args.bin_width),
        "--max-k",
        str(args.max_k),
    ])
    run([
        py,
        str(SCRIPTS / "simulate_poisson.py"),
        "--n",
        str(args.poisson_n),
        "--seed",
        str(args.poisson_seed),
        "--u-max",
        str(args.u_max),
        "--bin-width",
        str(args.bin_width),
        "--max-k",
        str(args.max_k),
    ])
    run([py, str(SCRIPTS / "make_figures.py")])
    write_metrics(args)
    write_hashes()
    print(f"metrics written to {(OUTPUTS / 'metrics.json').relative_to(PROJECT)}")
    print(f"hashes written to {(OUTPUTS / 'hashes.json').relative_to(PROJECT)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
