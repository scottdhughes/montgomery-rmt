#!/usr/bin/env python3
"""Finite GOE/GUE simulations for Montgomery-RMT Gate 0."""

from __future__ import annotations

import argparse
import csv
import math
from pathlib import Path

import numpy as np

from paircorr import paircorr_rows, write_rows as write_paircorr_rows


PROJECT = Path(__file__).resolve().parents[1]
PROCESSED = PROJECT / "data" / "processed"


def bulk_spacings(eigenvalues: np.ndarray, bulk_frac: float) -> np.ndarray:
    vals = np.sort(np.asarray(eigenvalues, dtype=float))
    n = len(vals)
    keep = max(3, int(n * bulk_frac))
    start = max((n - keep) // 2, 0)
    stop = min(start + keep, n)
    bulk = vals[start:stop]
    spacings = np.diff(bulk)
    mean = spacings.mean()
    if mean <= 0:
        return np.array([], dtype=float)
    return spacings / mean


def goe_matrix(rng: np.random.Generator, size: int) -> np.ndarray:
    a = rng.normal(size=(size, size))
    return (a + a.T) / math.sqrt(2 * size)


def gue_matrix(rng: np.random.Generator, size: int) -> np.ndarray:
    real = rng.normal(size=(size, size))
    imag = rng.normal(size=(size, size))
    a = real + 1j * imag
    return (a + a.conj().T) / math.sqrt(4 * size)


def simulate(ensemble: str, matrix_size: int, samples: int, bulk_frac: float, seed: int) -> np.ndarray:
    rng = np.random.default_rng(seed)
    all_spacings: list[np.ndarray] = []
    for _ in range(samples):
        if ensemble == "goe":
            matrix = goe_matrix(rng, matrix_size)
        elif ensemble == "gue":
            matrix = gue_matrix(rng, matrix_size)
        else:
            raise ValueError(f"unknown ensemble: {ensemble}")
        eigenvalues = np.linalg.eigvalsh(matrix)
        spacings = bulk_spacings(eigenvalues, bulk_frac)
        if len(spacings):
            all_spacings.append(spacings)
    if not all_spacings:
        return np.array([], dtype=float)
    return np.concatenate(all_spacings)


def write_spacing_csv(path: Path, spacings: np.ndarray, source: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="") as handle:
        writer = csv.DictWriter(
            handle,
            fieldnames=["index", "spacing_normalized", "source"],
            lineterminator="\n",
        )
        writer.writeheader()
        for index, value in enumerate(spacings, start=1):
            writer.writerow({"index": index, "spacing_normalized": float(value), "source": source})


def run_ensemble(
    ensemble: str,
    *,
    matrix_size: int,
    samples: int,
    bulk_frac: float,
    seed: int,
    u_max: float,
    bin_width: float,
    max_k: int,
) -> None:
    spacings = simulate(ensemble, matrix_size, samples, bulk_frac, seed)
    spacing_path = PROCESSED / f"{ensemble}_spacings.csv"
    paircorr_path = PROCESSED / f"{ensemble}_paircorr.csv"
    write_spacing_csv(spacing_path, spacings, ensemble)
    write_paircorr_rows(
        paircorr_path,
        paircorr_rows(spacings, u_max=u_max, bin_width=bin_width, max_k=max_k, label=ensemble),
    )
    print(f"{ensemble}: spacings={len(spacings)}")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--ensemble", choices=["goe", "gue", "both"], default="both")
    parser.add_argument("--matrix-size", type=int, default=80)
    parser.add_argument("--samples", type=int, default=25)
    parser.add_argument("--bulk-frac", type=float, default=0.6)
    parser.add_argument("--seed", type=int, default=1729)
    parser.add_argument("--u-max", type=float, default=5.0)
    parser.add_argument("--bin-width", type=float, default=0.05)
    parser.add_argument("--max-k", type=int, default=50)
    args = parser.parse_args()

    ensembles = ["goe", "gue"] if args.ensemble == "both" else [args.ensemble]
    for offset, ensemble in enumerate(ensembles):
        run_ensemble(
            ensemble,
            matrix_size=args.matrix_size,
            samples=args.samples,
            bulk_frac=args.bulk_frac,
            seed=args.seed + offset,
            u_max=args.u_max,
            bin_width=args.bin_width,
            max_k=args.max_k,
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
