#!/usr/bin/env python3
"""Compute normalized adjacent spacings for zeta zeros."""

from __future__ import annotations

import argparse
import csv
import math
from decimal import Decimal, InvalidOperation
from pathlib import Path


PROJECT = Path(__file__).resolve().parents[1]
DEFAULT_IN = PROJECT / "data" / "raw" / "zeta_zeros.csv"
DEFAULT_OUT = PROJECT / "data" / "processed" / "zeta_spacings.csv"
DEFAULT_LABEL = "gate0_default"


def load_zeros(path: Path, label: str) -> list[dict[str, str | int | Decimal]]:
    rows: list[dict[str, str | int | Decimal]] = []
    with path.open(newline="") as handle:
        reader = csv.DictReader(handle)
        for row in reader:
            try:
                index = int(row["index"])
                gamma_text = str(row["gamma"]).strip()
                gamma = Decimal(gamma_text)
            except (KeyError, TypeError, ValueError, InvalidOperation):
                continue
            if gamma > 0:
                rows.append(
                    {
                        "index": index,
                        "gamma": gamma,
                        "gamma_text": gamma_text,
                        "source": row.get("source") or "unknown",
                        "block_label": row.get("block_label") or label,
                    }
                )
    return rows


def compute_spacings(rows: list[dict[str, str | int | Decimal]], label: str) -> list[dict[str, float | int | str]]:
    out: list[dict[str, float | int | str]] = []
    two_pi = Decimal(str(2 * math.pi))
    for row, next_row in zip(rows, rows[1:]):
        gamma = row["gamma"]
        next_gamma = next_row["gamma"]
        if not isinstance(gamma, Decimal) or not isinstance(next_gamma, Decimal):
            continue
        spacing_raw = next_gamma - gamma
        if spacing_raw <= 0 or gamma <= two_pi:
            continue
        spacing_normalized = float(spacing_raw) * math.log(float(gamma) / (2 * math.pi)) / (2 * math.pi)
        if spacing_normalized > 0 and math.isfinite(spacing_normalized):
            out.append(
                {
                    "index": int(row["index"]),
                    "gamma": str(row["gamma_text"]),
                    "spacing_raw": format(spacing_raw, "f"),
                    "spacing_normalized": spacing_normalized,
                    "source": str(row["source"]),
                    "block_label": str(row["block_label"] or label),
                }
            )
    return out


def write_rows(path: Path, rows: list[dict[str, float | int | str]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="") as handle:
        writer = csv.DictWriter(
            handle,
            fieldnames=["index", "gamma", "spacing_raw", "spacing_normalized", "source", "block_label"],
            lineterminator="\n",
        )
        writer.writeheader()
        writer.writerows(rows)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", default=str(DEFAULT_IN))
    parser.add_argument("--output", default=str(DEFAULT_OUT))
    parser.add_argument("--label", default=DEFAULT_LABEL)
    args = parser.parse_args()

    in_path = Path(args.input)
    out_path = Path(args.output)
    if not in_path.is_absolute():
        in_path = PROJECT / in_path
    if not out_path.is_absolute():
        out_path = PROJECT / out_path

    rows = compute_spacings(load_zeros(in_path, args.label), args.label)
    write_rows(out_path, rows)
    print(f"zeta spacings: count={len(rows)} output={out_path.relative_to(PROJECT)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
