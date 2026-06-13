#!/usr/bin/env python3
"""Run Montgomery-RMT Gate 1-A low-vs-high block comparison."""

from __future__ import annotations

import argparse
import csv
import datetime as dt
import hashlib
import json
import math
import os
import platform
import subprocess
import sys
from pathlib import Path
from typing import Any

import numpy as np


PROJECT = Path(__file__).resolve().parents[1]
ROOT = PROJECT.parents[1]
SCRIPTS = PROJECT / "scripts"
DATA = PROJECT / "data"
RAW = DATA / "raw"
PROCESSED = DATA / "processed"
OUTPUTS = PROJECT / "outputs"
FIGURES = OUTPUTS / "figures"
BLOCKS_PATH = DATA / "odlyzko_blocks.json"
MANIFEST = DATA / "manifest.json"
HASHES = OUTPUTS / "hashes.json"
GATE1_METRICS = OUTPUTS / "gate1_metrics.json"

for cache_dir in [ROOT / ".matplotlib", ROOT / ".cache"]:
    cache_dir.mkdir(parents=True, exist_ok=True)

os.environ.setdefault("MPLBACKEND", "Agg")
os.environ.setdefault("MPLCONFIGDIR", str(ROOT / ".matplotlib"))
os.environ.setdefault("XDG_CACHE_HOME", str(ROOT / ".cache"))

import matplotlib.pyplot as plt


GATE1_FIGURES = [
    FIGURES / "gate1_paircorr_low_vs_high.png",
    FIGURES / "gate1_spacing_low_vs_high.png",
    FIGURES / "gate1_sine_kernel_residuals.png",
]

PUBLIC_LABELS = {
    "gate0_default": "Initial block",
    "block_1e12_10k": "10^12 block",
    "block_1e21_10k": "10^21 block",
    "block_1e22_10k": "10^22 block",
    "gue": "GUE",
    "goe": "GOE",
    "poisson": "Poisson",
}


def utc_now() -> str:
    fixed = os.environ.get("SPECTRAL_BRIDGE_TIMESTAMP")
    if fixed:
        return fixed
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


def load_json(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    try:
        return json.loads(path.read_text())
    except json.JSONDecodeError:
        return {}


def write_json(path: Path, data: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2, sort_keys=True) + "\n")


def project_rel(path: Path) -> str:
    return str(path.relative_to(PROJECT))


def public_label(label: str) -> str:
    return PUBLIC_LABELS.get(label, label)


def repo_display(text: str) -> str:
    path = Path(text)
    if not path.is_absolute():
        return text
    try:
        return str(path.relative_to(ROOT))
    except ValueError:
        pass
    try:
        return str(path.resolve().relative_to(ROOT.resolve()))
    except ValueError:
        return path.name


def display_command(argv: list[str]) -> list[str]:
    return [repo_display(item) for item in argv]


def project_path(text: str) -> Path:
    path = Path(text)
    return path if path.is_absolute() else PROJECT / path


def load_blocks() -> dict[str, dict[str, Any]]:
    data = json.loads(BLOCKS_PATH.read_text())
    return data["blocks"]


def update_hashes(paths: list[Path]) -> dict[str, str]:
    hashes = load_json(HASHES)
    for path in paths:
        if path.exists() and path.is_file():
            hashes[project_rel(path)] = sha256(path)
    write_json(HASHES, hashes)
    return hashes


def read_spacings(path: Path) -> np.ndarray:
    values: list[float] = []
    with path.open(newline="") as handle:
        reader = csv.DictReader(handle)
        for row in reader:
            try:
                value = float(row["spacing_normalized"])
            except (KeyError, TypeError, ValueError):
                continue
            if value > 0 and math.isfinite(value):
                values.append(value)
    return np.array(values, dtype=float)


def read_paircorr(path: Path) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    centers: list[float] = []
    density: list[float] = []
    sine: list[float] = []
    with path.open(newline="") as handle:
        reader = csv.DictReader(handle)
        for row in reader:
            try:
                centers.append(float(row["bin_center"]))
                density.append(float(row["density"]))
                sine.append(float(row["sine_kernel"]))
            except (KeyError, TypeError, ValueError):
                continue
    return np.array(centers, dtype=float), np.array(density, dtype=float), np.array(sine, dtype=float)


def spacing_stats(path: Path) -> dict[str, float | int | str]:
    values = read_spacings(path)
    if len(values) == 0:
        return {"path": project_rel(path), "count": 0}
    return {
        "path": project_rel(path),
        "count": int(len(values)),
        "mean": float(values.mean()),
        "std": float(values.std(ddof=1)) if len(values) > 1 else 0.0,
        "min": float(values.min()),
        "max": float(values.max()),
    }


def paircorr_stats(path: Path) -> dict[str, float | int | str]:
    centers, density, sine = read_paircorr(path)
    if len(centers) == 0:
        return {"path": project_rel(path), "bin_count": 0}
    residual = density - sine
    return {
        "path": project_rel(path),
        "bin_count": int(len(centers)),
        "l2_distance_to_sine": float(np.sqrt(np.mean(residual**2))),
        "mean_residual": float(residual.mean()),
        "max_abs_residual": float(np.max(np.abs(residual))),
    }


def zeta_block_paths(block: str) -> tuple[Path, Path, Path]:
    if block == "gate0_default":
        raw = RAW / "zeta_zeros.csv"
    else:
        metadata = load_blocks()[block]
        raw = project_path(str(metadata["normalized_csv"]))
    spacing = PROCESSED / f"gate1_{block}_spacings.csv"
    paircorr = PROCESSED / f"gate1_{block}_paircorr.csv"
    return raw, spacing, paircorr


def process_zeta_block(block: str, *, u_max: float, bin_width: float, max_k: int) -> dict[str, Any]:
    raw, spacing, paircorr = zeta_block_paths(block)
    if not raw.exists():
        raise FileNotFoundError(raw)
    py = sys.executable
    run(
        [
            py,
            str(SCRIPTS / "zeta_spacing.py"),
            "--input",
            project_rel(raw),
            "--output",
            project_rel(spacing),
            "--label",
            block,
        ]
    )
    run(
        [
            py,
            str(SCRIPTS / "paircorr.py"),
            "--input",
            project_rel(spacing),
            "--output",
            project_rel(paircorr),
            "--label",
            block,
            "--u-max",
            str(u_max),
            "--bin-width",
            str(bin_width),
            "--max-k",
            str(max_k),
        ]
    )
    return {
        "label": block,
        "kind": "zeta",
        "raw_path": project_rel(raw),
        "spacing_path": project_rel(spacing),
        "paircorr_path": project_rel(paircorr),
        "spacing": spacing_stats(spacing),
        "paircorr": paircorr_stats(paircorr),
    }


def control_entry(label: str) -> dict[str, Any]:
    spacing = PROCESSED / f"{label}_spacings.csv"
    paircorr = PROCESSED / f"{label}_paircorr.csv"
    if not spacing.exists() or not paircorr.exists():
        raise FileNotFoundError(f"missing {label} control outputs; run Gate 0 first")
    return {
        "label": label,
        "kind": "control",
        "spacing_path": project_rel(spacing),
        "paircorr_path": project_rel(paircorr),
        "spacing": spacing_stats(spacing),
        "paircorr": paircorr_stats(paircorr),
    }


def clear_gate1_figures() -> None:
    FIGURES.mkdir(parents=True, exist_ok=True)
    for path in GATE1_FIGURES:
        if path.exists():
            path.unlink()


def plot_paircorr(entries: list[dict[str, Any]], output: Path) -> None:
    plt.figure()
    sine_plotted = False
    for entry in entries:
        centers, density, sine = read_paircorr(PROJECT / entry["paircorr_path"])
        if len(centers) == 0:
            continue
        plt.plot(centers, density, label=public_label(str(entry["label"])))
        if not sine_plotted:
            plt.plot(centers, sine, linestyle="--", label="Sine-kernel reference")
            sine_plotted = True
    plt.title("Finite pair-sum density estimates")
    plt.xlabel("u")
    plt.ylabel("density")
    plt.legend()
    plt.tight_layout()
    output.parent.mkdir(parents=True, exist_ok=True)
    plt.savefig(output, dpi=160)
    plt.close()


def plot_spacing(entries: list[dict[str, Any]], output: Path) -> None:
    plt.figure()
    for entry in entries:
        values = read_spacings(PROJECT / entry["spacing_path"])
        if len(values) == 0:
            continue
        plt.hist(values, bins=60, density=True, histtype="step", label=public_label(str(entry["label"])))
    plt.title("Default nearest-neighbor spacing diagnostics")
    plt.xlabel("normalized nearest-neighbor spacing")
    plt.ylabel("density")
    plt.legend()
    plt.tight_layout()
    output.parent.mkdir(parents=True, exist_ok=True)
    plt.savefig(output, dpi=160)
    plt.close()


def plot_residuals(entries: list[dict[str, Any]], output: Path) -> None:
    plt.figure()
    for entry in entries:
        centers, density, sine = read_paircorr(PROJECT / entry["paircorr_path"])
        if len(centers) == 0:
            continue
        plt.plot(centers, density - sine, label=public_label(str(entry["label"])))
    plt.axhline(0.0, linestyle="--", linewidth=1.0)
    plt.title("Residuals from sine-kernel reference")
    plt.xlabel("u")
    plt.ylabel("density minus sine-kernel reference")
    plt.legend()
    plt.tight_layout()
    output.parent.mkdir(parents=True, exist_ok=True)
    plt.savefig(output, dpi=160)
    plt.close()


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--blocks", default="gate0_default,block_1e12_10k,block_1e21_10k,block_1e22_10k")
    parser.add_argument("--require-high", action="store_true")
    parser.add_argument("--u-max", type=float, default=5.0)
    parser.add_argument("--bin-width", type=float, default=0.05)
    parser.add_argument("--max-k", type=int, default=50)
    args = parser.parse_args()

    requested = [item.strip() for item in args.blocks.split(",") if item.strip()]
    known_blocks = set(load_blocks()) | {"gate0_default"}
    unknown = [block for block in requested if block not in known_blocks]
    if unknown:
        raise SystemExit(f"unknown block(s): {', '.join(unknown)}")

    included: list[dict[str, Any]] = []
    missing: list[dict[str, str]] = []
    high_found = False

    for block in requested:
        try:
            entry = process_zeta_block(block, u_max=args.u_max, bin_width=args.bin_width, max_k=args.max_k)
        except FileNotFoundError:
            raw, _spacing, _paircorr = zeta_block_paths(block)
            if block == "gate0_default":
                raise SystemExit(
                    "Gate 1 requires Gate 0 raw zeta data. Run "
                    ".venv/bin/python projects/montgomery-rmt/scripts/run_gate0.py first."
                )
            missing.append(
                {
                    "label": block,
                    "expected_path": project_rel(raw),
                    "fetch_command": (
                        ".venv/bin/python projects/montgomery-rmt/scripts/fetch_odlyzko_blocks.py "
                        f"--block {block} --download --timeout 60"
                    ),
                }
            )
            continue
        included.append(entry)
        if block != "gate0_default":
            high_found = True

    if args.require_high and not high_found:
        raise SystemExit("--require-high was passed, but no high Odlyzko block CSVs were found")

    for label in ["gue", "goe", "poisson"]:
        included.append(control_entry(label))

    clear_gate1_figures()
    plot_paircorr(included, GATE1_FIGURES[0])
    plot_spacing(included, GATE1_FIGURES[1])
    plot_residuals(included, GATE1_FIGURES[2])

    generated_paths = [
        *(PROJECT / entry["spacing_path"] for entry in included if entry["kind"] == "zeta"),
        *(PROJECT / entry["paircorr_path"] for entry in included if entry["kind"] == "zeta"),
        *GATE1_FIGURES,
    ]
    hashes = update_hashes([path for path in generated_paths if path.exists()])

    metrics = {
        "generated_at_utc": utc_now(),
        "command": display_command(sys.argv[:]),
        "python_executable": repo_display(sys.executable),
        "python_version": sys.version,
        "platform": platform.platform(),
        "requested_blocks": requested,
        "included_blocks": [entry["label"] for entry in included],
        "missing_blocks": missing,
        "high_blocks_found": high_found,
        "require_high": bool(args.require_high),
        "histogram_parameters": {
            "u_max": args.u_max,
            "bin_width": args.bin_width,
            "max_k": args.max_k,
        },
        "entries": included,
        "figures": [project_rel(path) for path in GATE1_FIGURES],
        "hashes": {project_rel(path): hashes.get(project_rel(path)) for path in generated_paths if path.exists()},
        "instructions": {
            "fetch_high_block_example": (
                ".venv/bin/python projects/montgomery-rmt/scripts/fetch_odlyzko_blocks.py "
                "--block block_1e12_10k --download --timeout 60"
            )
        },
    }
    write_json(GATE1_METRICS, metrics)
    update_hashes([GATE1_METRICS])

    if missing:
        print("Gate 1 ran in low-only or partial mode. Missing high blocks:")
        for item in missing:
            print(f"- {item['label']}: fetch with `{item['fetch_command']}`")
    print(f"gate1 metrics written to {GATE1_METRICS.relative_to(PROJECT)}")
    for path in GATE1_FIGURES:
        print(f"figure written: {path.relative_to(PROJECT)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
