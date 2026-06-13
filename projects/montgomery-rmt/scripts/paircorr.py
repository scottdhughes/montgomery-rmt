#!/usr/bin/env python3
"""Finite pair-correlation-style histograms from normalized spacings."""

from __future__ import annotations

import argparse
import csv
import math
from pathlib import Path

import numpy as np


PROJECT = Path(__file__).resolve().parents[1]
DEFAULT_IN = PROJECT / "data" / "processed" / "zeta_spacings.csv"
DEFAULT_OUT = PROJECT / "data" / "processed" / "zeta_paircorr.csv"
DEFAULT_LABEL = "gate0_default"


def sine_kernel(u: np.ndarray) -> np.ndarray:
    values = np.zeros_like(u, dtype=float)
    mask = u != 0
    x = math.pi * u[mask]
    values[mask] = 1.0 - (np.sin(x) / x) ** 2
    return values


def load_spacings(path: Path) -> np.ndarray:
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


def paircorr_rows(
    spacings: np.ndarray,
    *,
    u_max: float,
    bin_width: float,
    max_k: int,
    label: str = DEFAULT_LABEL,
) -> list[dict[str, float | str]]:
    bins = np.arange(0.0, u_max + bin_width, bin_width)
    counts = np.zeros(len(bins) - 1, dtype=float)
    n_points = len(spacings) + 1
    if len(spacings) == 0:
        centers = (bins[:-1] + bins[1:]) / 2
        density = counts
    else:
        max_window = min(max_k, len(spacings))
        for start in range(len(spacings)):
            running = 0.0
            for width in range(1, max_window + 1):
                stop = start + width - 1
                if stop >= len(spacings):
                    break
                running += float(spacings[stop])
                if running > u_max:
                    break
                bin_index = int(running / bin_width)
                if 0 <= bin_index < len(counts):
                    counts[bin_index] += 1
        density = counts / (max(n_points, 1) * bin_width)
        centers = (bins[:-1] + bins[1:]) / 2

    reference = sine_kernel(centers)
    return [
        {
            "block_label": label,
            "bin_left": float(left),
            "bin_right": float(right),
            "bin_center": float(center),
            "density": float(value),
            "sine_kernel": float(ref),
        }
        for left, right, center, value, ref in zip(bins[:-1], bins[1:], centers, density, reference)
    ]


def write_rows(path: Path, rows: list[dict[str, float | str]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="") as handle:
        writer = csv.DictWriter(
            handle,
            fieldnames=["block_label", "bin_left", "bin_right", "bin_center", "density", "sine_kernel"],
            lineterminator="\n",
        )
        writer.writeheader()
        writer.writerows(rows)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", default=str(DEFAULT_IN))
    parser.add_argument("--output", default=str(DEFAULT_OUT))
    parser.add_argument("--u-max", type=float, default=5.0)
    parser.add_argument("--bin-width", type=float, default=0.05)
    parser.add_argument("--max-k", type=int, default=50)
    parser.add_argument("--label", default=DEFAULT_LABEL)
    args = parser.parse_args()

    in_path = Path(args.input)
    out_path = Path(args.output)
    if not in_path.is_absolute():
        in_path = PROJECT / in_path
    if not out_path.is_absolute():
        out_path = PROJECT / out_path

    rows = paircorr_rows(
        load_spacings(in_path),
        u_max=args.u_max,
        bin_width=args.bin_width,
        max_k=args.max_k,
        label=args.label,
    )
    write_rows(out_path, rows)
    print(f"paircorr: bins={len(rows)} output={out_path.relative_to(PROJECT)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
