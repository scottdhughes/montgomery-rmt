#!/usr/bin/env python3
"""Poisson negative control for Montgomery-RMT Gate 0."""

from __future__ import annotations

import argparse
import csv
from pathlib import Path

import numpy as np

from paircorr import paircorr_rows, write_rows as write_paircorr_rows


PROJECT = Path(__file__).resolve().parents[1]
PROCESSED = PROJECT / "data" / "processed"


def write_spacing_csv(path: Path, spacings: np.ndarray) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="") as handle:
        writer = csv.DictWriter(
            handle,
            fieldnames=["index", "spacing_normalized", "source"],
            lineterminator="\n",
        )
        writer.writeheader()
        for index, value in enumerate(spacings, start=1):
            writer.writerow({"index": index, "spacing_normalized": float(value), "source": "poisson"})


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--n", type=int, default=10000)
    parser.add_argument("--seed", type=int, default=314159)
    parser.add_argument("--u-max", type=float, default=5.0)
    parser.add_argument("--bin-width", type=float, default=0.05)
    parser.add_argument("--max-k", type=int, default=50)
    args = parser.parse_args()

    rng = np.random.default_rng(args.seed)
    spacings = rng.exponential(scale=1.0, size=args.n)
    write_spacing_csv(PROCESSED / "poisson_spacings.csv", spacings)
    write_paircorr_rows(
        PROCESSED / "poisson_paircorr.csv",
        paircorr_rows(spacings, u_max=args.u_max, bin_width=args.bin_width, max_k=args.max_k, label="poisson"),
    )
    print(f"poisson: spacings={len(spacings)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
