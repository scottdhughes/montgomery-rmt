#!/usr/bin/env python3
"""Gate 1-B sensitivity audit for Montgomery-RMT finite diagnostics."""

from __future__ import annotations

import argparse
import csv
import datetime as dt
import json
import math
import os
import platform
import statistics
import sys
from collections import defaultdict
from pathlib import Path
from typing import Any

import numpy as np

from paircorr import paircorr_rows
from simulate_rmt import simulate as simulate_rmt
from zeta_spacing import compute_spacings, load_zeros


PROJECT = Path(__file__).resolve().parents[1]
ROOT = PROJECT.parents[1]
DATA = PROJECT / "data"
RAW = DATA / "raw"
PROCESSED = DATA / "processed"
OUTPUTS = PROJECT / "outputs"
FIGURES = OUTPUTS / "figures"
METRICS = OUTPUTS / "gate1_sensitivity_metrics.json"
SUMMARY_CSV = PROCESSED / "gate1_sensitivity_summary.csv"

for cache_dir in [ROOT / ".matplotlib", ROOT / ".cache"]:
    cache_dir.mkdir(parents=True, exist_ok=True)

os.environ.setdefault("MPLBACKEND", "Agg")
os.environ.setdefault("MPLCONFIGDIR", str(ROOT / ".matplotlib"))
os.environ.setdefault("XDG_CACHE_HOME", str(ROOT / ".cache"))

import matplotlib.pyplot as plt


ZETA_BLOCK_PATHS = {
    "gate0_default": RAW / "zeta_zeros.csv",
    "block_1e12_10k": RAW / "zeta_zeros_block_1e12_10k.csv",
    "block_1e21_10k": RAW / "zeta_zeros_block_1e21_10k.csv",
    "block_1e22_10k": RAW / "zeta_zeros_block_1e22_10k.csv",
}
DEFAULT_BLOCKS = ["gate0_default", "block_1e12_10k"]
POISSON_SEED = 314159
POISSON_N = 10000
BULK_FRAC = 0.6
DEFAULT_FIGURE_PREFIX = "gate1_sensitivity_"
FIGURE_SUFFIXES = (
    "high_minus_low_l2.png",
    "l2_by_bin_width.png",
    "rmt_controls.png",
)
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


def parse_float_list(text: str) -> list[float]:
    return [float(item.strip()) for item in text.split(",") if item.strip()]


def parse_int_list(text: str) -> list[int]:
    return [int(item.strip()) for item in text.split(",") if item.strip()]


def parse_blocks(text: str) -> list[str]:
    blocks = [item.strip() for item in text.split(",") if item.strip()]
    unknown = [block for block in blocks if block not in ZETA_BLOCK_PATHS]
    if unknown:
        raise SystemExit(f"unknown zeta block(s): {', '.join(unknown)}")
    if "gate0_default" not in blocks:
        raise SystemExit("--blocks must include gate0_default as the baseline")
    if len(blocks) < 2:
        raise SystemExit("--blocks must include at least one high Odlyzko block")
    return blocks


def project_rel(path: Path) -> str:
    return str(path.relative_to(PROJECT))


def figure_paths(prefix: str) -> list[Path]:
    clean = prefix.strip()
    if not clean:
        raise SystemExit("--figure-prefix must be nonempty")
    if any(part in clean for part in ("/", "\\")):
        raise SystemExit("--figure-prefix must be a filename prefix, not a path")
    return [FIGURES / f"{clean}{suffix}" for suffix in FIGURE_SUFFIXES]


def run_label(fast: bool) -> str:
    return "Fast check" if fast else "Sensitivity grid"


def public_label(label: str) -> str:
    return PUBLIC_LABELS.get(label, label)


def mean_or_none(values: np.ndarray) -> float | None:
    return float(values.mean()) if len(values) else None


def median(values: list[float]) -> float | None:
    return float(statistics.median(values)) if values else None


def minmax(values: list[float]) -> dict[str, float | None]:
    if not values:
        return {"min": None, "max": None}
    return {"min": float(min(values)), "max": float(max(values))}


def finite_stats(values: np.ndarray) -> dict[str, float | int | None]:
    if len(values) == 0:
        return {"count": 0, "mean": None, "std": None, "min": None, "max": None}
    return {
        "count": int(len(values)),
        "mean": float(values.mean()),
        "std": float(values.std(ddof=1)) if len(values) > 1 else 0.0,
        "min": float(values.min()),
        "max": float(values.max()),
    }


def pair_metrics(spacings: np.ndarray, *, u_max: float, bin_width: float, max_k: int, label: str) -> dict[str, Any]:
    rows = paircorr_rows(spacings, u_max=u_max, bin_width=bin_width, max_k=max_k, label=label)
    density = np.array([float(row["density"]) for row in rows], dtype=float)
    sine = np.array([float(row["sine_kernel"]) for row in rows], dtype=float)
    residual = density - sine
    return {
        "bin_count": int(len(rows)),
        "l2_to_sine_kernel": float(np.sqrt(np.mean(residual**2))) if len(residual) else None,
        "mean_residual": float(residual.mean()) if len(residual) else None,
        "max_abs_residual": float(np.max(np.abs(residual))) if len(residual) else None,
    }


def zeta_spacings(path: Path, label: str) -> np.ndarray:
    if not path.exists():
        raise SystemExit(f"required local zeta data missing: {path.relative_to(PROJECT)}")
    rows = compute_spacings(load_zeros(path, label), label)
    return np.array([float(row["spacing_normalized"]) for row in rows], dtype=float)


def summary_row(
    *,
    config_id: str,
    source: str,
    bin_width: float,
    u_max: float,
    max_k: int,
    matrix_size: int | None,
    samples: int | None,
    seed: int | None,
    l2: float | None,
    mean_spacing: float | None,
    notes: str,
) -> dict[str, str]:
    return {
        "config_id": config_id,
        "source": source,
        "bin_width": f"{bin_width:g}",
        "u_max": f"{u_max:g}",
        "max_k": str(max_k),
        "matrix_size": "" if matrix_size is None else str(matrix_size),
        "samples": "" if samples is None else str(samples),
        "seed": "" if seed is None else str(seed),
        "l2_to_sine_kernel": "" if l2 is None else f"{l2:.12g}",
        "mean_normalized_spacing": "" if mean_spacing is None else f"{mean_spacing:.12g}",
        "notes": notes,
    }


def write_summary_csv(rows: list[dict[str, str]]) -> None:
    SUMMARY_CSV.parent.mkdir(parents=True, exist_ok=True)
    fieldnames = [
        "config_id",
        "source",
        "bin_width",
        "u_max",
        "max_k",
        "matrix_size",
        "samples",
        "seed",
        "l2_to_sine_kernel",
        "mean_normalized_spacing",
        "notes",
    ]
    with SUMMARY_CSV.open("w", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames, lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)


def hist_configs(bin_widths: list[float], u_max_values: list[float], max_k_values: list[int]) -> list[dict[str, Any]]:
    configs: list[dict[str, Any]] = []
    counter = 1
    for bin_width in bin_widths:
        for u_max in u_max_values:
            for max_k in max_k_values:
                configs.append(
                    {
                        "hist_config_id": f"h{counter:03d}",
                        "bin_width": float(bin_width),
                        "u_max": float(u_max),
                        "max_k": int(max_k),
                    }
                )
                counter += 1
    return configs


def row_float(row: dict[str, Any], field: str) -> float:
    value = row.get(field)
    if value is None:
        return math.nan
    return float(value)


def aggregate_zeta(rows: list[dict[str, Any]], zeta_blocks: list[str]) -> dict[str, Any]:
    zeta = [row for row in rows if row["kind"] == "zeta"]
    by_hist: dict[tuple[float, float, int], dict[str, dict[str, Any]]] = defaultdict(dict)
    for row in zeta:
        key = (float(row["bin_width"]), float(row["u_max"]), int(row["max_k"]))
        by_hist[key][row["source"]] = row

    baseline = zeta_blocks[0]
    primary_high = zeta_blocks[1]
    block_summaries: dict[str, dict[str, Any]] = {}
    for block in zeta_blocks:
        block_rows = [row for row in zeta if row["source"] == block]
        l2_values = [row_float(row, "l2_to_sine_kernel") for row in block_rows]
        block_summaries[block] = {
            "configuration_count": len(block_rows),
            "median_l2": median(l2_values),
            "l2_range": minmax(l2_values),
            "median_mean_normalized_spacing": median(
                [row_float(row.get("spacing", {}), "mean") for row in block_rows if row.get("spacing")]
            ),
        }

    comparisons: list[dict[str, Any]] = []
    pairwise: dict[str, list[dict[str, Any]]] = {block: [] for block in zeta_blocks[1:]}
    monotone_comparisons: list[dict[str, Any]] = []
    for key, grouped in sorted(by_hist.items()):
        low = grouped.get(baseline)
        high = grouped.get(primary_high)
        if not low or not high:
            continue
        delta = row_float(high, "l2_to_sine_kernel") - row_float(low, "l2_to_sine_kernel")
        comparisons.append(
            {
                "bin_width": key[0],
                "u_max": key[1],
                "max_k": key[2],
                "low_l2": row_float(low, "l2_to_sine_kernel"),
                "high_l2": row_float(high, "l2_to_sine_kernel"),
                "high_minus_low_l2": float(delta),
                "high_beats_low": bool(delta < 0),
            }
        )
        for block in zeta_blocks[1:]:
            other = grouped.get(block)
            if not other:
                continue
            pair_delta = row_float(other, "l2_to_sine_kernel") - row_float(low, "l2_to_sine_kernel")
            pairwise[block].append(
                {
                    "bin_width": key[0],
                    "u_max": key[1],
                    "max_k": key[2],
                    "baseline_l2": row_float(low, "l2_to_sine_kernel"),
                    "block_l2": row_float(other, "l2_to_sine_kernel"),
                    "block_minus_baseline_l2": float(pair_delta),
                    "block_beats_baseline": bool(pair_delta < 0),
                }
            )
        if all(block in grouped for block in zeta_blocks):
            l2_sequence = [row_float(grouped[block], "l2_to_sine_kernel") for block in zeta_blocks]
            monotone = all(left > right for left, right in zip(l2_sequence, l2_sequence[1:]))
            monotone_comparisons.append(
                {
                    "bin_width": key[0],
                    "u_max": key[1],
                    "max_k": key[2],
                    "blocks": zeta_blocks,
                    "l2_sequence": l2_sequence,
                    "strictly_decreasing": bool(monotone),
                }
            )

    high_wins = sum(1 for item in comparisons if item["high_beats_low"])
    total = len(comparisons)
    low_l2 = [item["low_l2"] for item in comparisons]
    high_l2 = [item["high_l2"] for item in comparisons]
    deltas = [item["high_minus_low_l2"] for item in comparisons]
    low_le_high = total - high_wins
    median_delta = median(deltas)
    win_rate = high_wins / total if total else 0.0
    if total and win_rate >= 0.7 and median_delta is not None and median_delta < 0:
        verdict = "robust"
    elif total and high_wins > 0:
        verdict = "mixed"
    else:
        verdict = "not_supported"

    by_dimension: dict[str, dict[str, Any]] = {}
    for dimension in ["bin_width", "u_max", "max_k"]:
        values: dict[str, dict[str, Any]] = {}
        for item in comparisons:
            key = f"{item[dimension]:g}" if isinstance(item[dimension], float) else str(item[dimension])
            values.setdefault(key, {"total": 0, "high_wins": 0, "deltas": []})
            values[key]["total"] += 1
            values[key]["high_wins"] += int(item["high_beats_low"])
            values[key]["deltas"].append(item["high_minus_low_l2"])
        by_dimension[dimension] = {
            key: {
                "total": value["total"],
                "high_wins": value["high_wins"],
                "low_le_high": value["total"] - value["high_wins"],
                "median_high_minus_low_l2": median(value["deltas"]),
            }
            for key, value in sorted(values.items())
        }

    pairwise_vs_baseline: dict[str, dict[str, Any]] = {}
    for block, items in pairwise.items():
        wins = sum(1 for item in items if item["block_beats_baseline"])
        deltas = [item["block_minus_baseline_l2"] for item in items]
        pairwise_vs_baseline[block] = {
            "total_configurations": len(items),
            "block_lt_baseline_count": wins,
            "baseline_le_block_count": len(items) - wins,
            "median_block_minus_baseline_l2": median(deltas),
            "block_l2_range": minmax([item["block_l2"] for item in items]),
            "baseline_l2_range": minmax([item["baseline_l2"] for item in items]),
        }

    monotone_count = sum(1 for item in monotone_comparisons if item["strictly_decreasing"])
    return {
        "verdict": verdict,
        "baseline": baseline,
        "primary_high_block": primary_high,
        "zeta_blocks": zeta_blocks,
        "total_configurations": total,
        "high_lt_low_count": high_wins,
        "low_le_high_count": low_le_high,
        "median_low_l2": median(low_l2),
        "median_high_l2": median(high_l2),
        "low_l2_range": minmax(low_l2),
        "high_l2_range": minmax(high_l2),
        "median_high_minus_low_l2": median_delta,
        "best_case": min(comparisons, key=lambda item: item["high_minus_low_l2"]) if comparisons else None,
        "worst_case": max(comparisons, key=lambda item: item["high_minus_low_l2"]) if comparisons else None,
        "by_dimension": by_dimension,
        "block_summaries": block_summaries,
        "pairwise_vs_baseline": pairwise_vs_baseline,
        "monotone_trend": {
            "blocks": zeta_blocks,
            "total_configurations": len(monotone_comparisons),
            "strictly_decreasing_count": monotone_count,
            "not_strictly_decreasing_count": len(monotone_comparisons) - monotone_count,
            "all_strictly_decreasing": bool(monotone_comparisons and monotone_count == len(monotone_comparisons)),
            "comparisons": monotone_comparisons,
        },
        "comparisons": comparisons,
    }


def aggregate_rmt(rows: list[dict[str, Any]]) -> dict[str, Any]:
    poisson_by_hist: dict[tuple[float, float, int], dict[str, Any]] = {}
    for row in rows:
        if row["source"] != "poisson":
            continue
        key = (float(row["bin_width"]), float(row["u_max"]), int(row["max_k"]))
        poisson_by_hist[key] = row

    gue_rows = [row for row in rows if row["source"] == "gue"]
    goe_rows = [row for row in rows if row["source"] == "goe"]
    poisson_rows = [row for row in rows if row["source"] == "poisson"]
    comparisons: list[dict[str, Any]] = []
    for row in gue_rows:
        key = (float(row["bin_width"]), float(row["u_max"]), int(row["max_k"]))
        poisson = poisson_by_hist.get(key)
        if not poisson:
            continue
        gue_l2 = row_float(row, "l2_to_sine_kernel")
        poisson_l2 = row_float(poisson, "l2_to_sine_kernel")
        comparisons.append(
            {
                "bin_width": key[0],
                "u_max": key[1],
                "max_k": key[2],
                "matrix_size": row.get("matrix_size"),
                "samples": row.get("samples"),
                "gue_l2": gue_l2,
                "poisson_l2": poisson_l2,
                "gue_beats_poisson": bool(gue_l2 < poisson_l2),
            }
        )

    wins = sum(1 for item in comparisons if item["gue_beats_poisson"])
    total = len(comparisons)
    return {
        "gue_lt_poisson_count": wins,
        "gue_ge_poisson_count": total - wins,
        "total_comparisons": total,
        "median_gue_l2": median([row_float(row, "l2_to_sine_kernel") for row in gue_rows]),
        "median_goe_l2": median([row_float(row, "l2_to_sine_kernel") for row in goe_rows]),
        "median_poisson_l2": median([row_float(row, "l2_to_sine_kernel") for row in poisson_rows]),
        "gue_l2_range": minmax([row_float(row, "l2_to_sine_kernel") for row in gue_rows]),
        "poisson_l2_range": minmax([row_float(row, "l2_to_sine_kernel") for row in poisson_rows]),
        "comparisons": comparisons,
    }


def plot_high_minus_low(comparisons: list[dict[str, Any]], output: Path, *, fast: bool) -> None:
    output.parent.mkdir(parents=True, exist_ok=True)
    ordered = sorted(comparisons, key=lambda item: (item["bin_width"], item["u_max"], item["max_k"]))
    plt.figure()
    xs = list(range(1, len(ordered) + 1))
    ys = [item["high_minus_low_l2"] for item in ordered]
    plt.plot(xs, ys, marker="o")
    plt.axhline(0.0, linestyle="--", linewidth=1.0)
    plt.title("Fast check: high-minus-low RMS" if fast else "Full-grid high-minus-low residual sensitivity")
    plt.xlabel("zeta sensitivity configuration")
    plt.ylabel("D(high block) - D(initial block)")
    plt.tight_layout()
    plt.savefig(output, dpi=160)
    plt.close()


def plot_l2_by_bin_width(rows: list[dict[str, Any]], zeta_blocks: list[str], output: Path, *, fast: bool) -> None:
    zeta = [row for row in rows if row["source"] in set(zeta_blocks)]
    grouped: dict[str, dict[float, list[float]]] = {block: defaultdict(list) for block in zeta_blocks}
    for row in zeta:
        grouped[row["source"]][float(row["bin_width"])].append(row_float(row, "l2_to_sine_kernel"))
    plt.figure()
    for source, by_width in grouped.items():
        widths = sorted(by_width)
        medians = [median(by_width[width]) for width in widths]
        plt.plot(widths, medians, marker="o", label=public_label(source))
    plt.title("Fast check: zeta residual by bin width" if fast else "Zeta residuals by bin width")
    plt.xlabel("bin width")
    plt.ylabel("median discrete RMS residual")
    plt.legend()
    plt.tight_layout()
    plt.savefig(output, dpi=160)
    plt.close()


def plot_rmt_controls(rows: list[dict[str, Any]], output: Path, *, fast: bool) -> None:
    labels = ["gue", "goe", "poisson"]
    medians = []
    for label in labels:
        medians.append(median([row_float(row, "l2_to_sine_kernel") for row in rows if row["source"] == label]))
    plt.figure()
    plt.bar([public_label(label) for label in labels], medians)
    plt.title("Fast check: RMT and Poisson medians" if fast else "RMT and Poisson control medians")
    plt.xlabel("source")
    plt.ylabel("median discrete RMS residual")
    plt.tight_layout()
    plt.savefig(output, dpi=160)
    plt.close()


def run_sensitivity(args: argparse.Namespace) -> dict[str, Any]:
    zeta_blocks = parse_blocks(args.blocks)
    fig_paths = figure_paths(args.figure_prefix)
    if args.fast:
        bin_widths = [0.05, 0.1]
        u_max_values = [5.0]
        max_k_values = [50, 100]
        matrix_sizes = [80]
        samples_values = [15]
    else:
        bin_widths = parse_float_list(args.bin_widths)
        u_max_values = parse_float_list(args.u_max_values)
        max_k_values = parse_int_list(args.max_k_values)
        matrix_sizes = parse_int_list(args.matrix_sizes)
        samples_values = parse_int_list(args.samples_values)

    hist_grid = hist_configs(bin_widths, u_max_values, max_k_values)
    zeta_cache = {label: zeta_spacings(ZETA_BLOCK_PATHS[label], label) for label in zeta_blocks}
    poisson_spacings = np.random.default_rng(POISSON_SEED).exponential(scale=1.0, size=POISSON_N)

    rows: list[dict[str, Any]] = []
    csv_rows: list[dict[str, str]] = []

    for hist in hist_grid:
        for source, spacings in zeta_cache.items():
            metrics = pair_metrics(
                spacings,
                u_max=hist["u_max"],
                bin_width=hist["bin_width"],
                max_k=hist["max_k"],
                label=source,
            )
            row = {
                "config_id": hist["hist_config_id"],
                "kind": "zeta",
                "source": source,
                "bin_width": hist["bin_width"],
                "u_max": hist["u_max"],
                "max_k": hist["max_k"],
                "matrix_size": None,
                "samples": None,
                "seed": None,
                "spacing": finite_stats(spacings),
                **metrics,
                "notes": "existing zeta block; no data fetched",
            }
            rows.append(row)
            csv_rows.append(
                summary_row(
                    config_id=hist["hist_config_id"],
                    source=source,
                    bin_width=hist["bin_width"],
                    u_max=hist["u_max"],
                    max_k=hist["max_k"],
                    matrix_size=None,
                    samples=None,
                    seed=None,
                    l2=row["l2_to_sine_kernel"],
                    mean_spacing=mean_or_none(spacings),
                    notes=row["notes"],
                )
            )

        metrics = pair_metrics(
            poisson_spacings,
            u_max=hist["u_max"],
            bin_width=hist["bin_width"],
            max_k=hist["max_k"],
            label="poisson",
        )
        row = {
            "config_id": hist["hist_config_id"],
            "kind": "control",
            "source": "poisson",
            "bin_width": hist["bin_width"],
            "u_max": hist["u_max"],
            "max_k": hist["max_k"],
            "matrix_size": None,
            "samples": None,
            "seed": POISSON_SEED,
            "spacing": finite_stats(poisson_spacings),
            **metrics,
            "notes": "Poisson negative control",
        }
        rows.append(row)
        csv_rows.append(
            summary_row(
                config_id=hist["hist_config_id"],
                source="poisson",
                bin_width=hist["bin_width"],
                u_max=hist["u_max"],
                max_k=hist["max_k"],
                matrix_size=None,
                samples=None,
                seed=POISSON_SEED,
                l2=row["l2_to_sine_kernel"],
                mean_spacing=mean_or_none(poisson_spacings),
                notes=row["notes"],
            )
        )

    rmt_cache: dict[tuple[str, int, int], tuple[int, np.ndarray]] = {}
    for matrix_size in matrix_sizes:
        for samples in samples_values:
            for source, seed_offset in [("gue", 1), ("goe", 0)]:
                seed = args.seed + seed_offset
                rmt_cache[(source, matrix_size, samples)] = (
                    seed,
                    simulate_rmt(source, matrix_size, samples, BULK_FRAC, seed),
                )

    for hist in hist_grid:
        for (source, matrix_size, samples), (seed, spacings) in rmt_cache.items():
            metrics = pair_metrics(
                spacings,
                u_max=hist["u_max"],
                bin_width=hist["bin_width"],
                max_k=hist["max_k"],
                label=source,
            )
            row = {
                "config_id": f"{hist['hist_config_id']}_m{matrix_size}_s{samples}",
                "kind": "control",
                "source": source,
                "bin_width": hist["bin_width"],
                "u_max": hist["u_max"],
                "max_k": hist["max_k"],
                "matrix_size": matrix_size,
                "samples": samples,
                "seed": seed,
                "spacing": finite_stats(spacings),
                **metrics,
                "notes": "GUE sine-kernel comparison" if source == "gue" else "GOE contrast ensemble",
            }
            rows.append(row)
            csv_rows.append(
                summary_row(
                    config_id=row["config_id"],
                    source=source,
                    bin_width=hist["bin_width"],
                    u_max=hist["u_max"],
                    max_k=hist["max_k"],
                    matrix_size=matrix_size,
                    samples=samples,
                    seed=seed,
                    l2=row["l2_to_sine_kernel"],
                    mean_spacing=mean_or_none(spacings),
                    notes=row["notes"],
                )
            )

    zeta_aggregate = aggregate_zeta(rows, zeta_blocks)
    rmt_aggregate = aggregate_rmt(rows)
    plot_high_minus_low(zeta_aggregate["comparisons"], fig_paths[0], fast=bool(args.fast))
    plot_l2_by_bin_width(rows, zeta_blocks, fig_paths[1], fast=bool(args.fast))
    plot_rmt_controls(rows, fig_paths[2], fast=bool(args.fast))
    write_summary_csv(csv_rows)

    return {
        "generated_at_utc": utc_now(),
        "command": sys.argv[:],
        "python_version": sys.version,
        "platform": platform.platform(),
        "input_blocks": {label: project_rel(ZETA_BLOCK_PATHS[label]) for label in zeta_blocks},
        "grid": {
            "bin_widths": bin_widths,
            "u_max_values": u_max_values,
            "max_k_values": max_k_values,
            "matrix_sizes": matrix_sizes,
            "samples_values": samples_values,
            "fast": bool(args.fast),
        },
        "random_seeds": {
            "rmt_base": args.seed,
            "gue": args.seed + 1,
            "goe": args.seed,
            "poisson": POISSON_SEED,
        },
        "summary_csv": project_rel(SUMMARY_CSV),
        "figure_prefix": args.figure_prefix,
        "figures": [project_rel(path) for path in fig_paths],
        "per_configuration_metrics": rows,
        "aggregate_verdicts": {
            "high_vs_low": zeta_aggregate,
            "rmt_controls": rmt_aggregate,
        },
        "boundary": "finite numerical evidence only; no theorem claim",
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--bin-widths", default="0.025,0.05,0.1")
    parser.add_argument("--u-max-values", default="3,5,8")
    parser.add_argument("--max-k-values", default="25,50,100")
    parser.add_argument("--matrix-sizes", default="60,80,120")
    parser.add_argument("--samples-values", default="15,25")
    parser.add_argument("--seed", type=int, default=1729)
    parser.add_argument("--blocks", default=",".join(DEFAULT_BLOCKS))
    parser.add_argument(
        "--figure-prefix",
        default=DEFAULT_FIGURE_PREFIX,
        help="Filename prefix for sensitivity figures under outputs/figures.",
    )
    parser.add_argument("--fast", action="store_true")
    args = parser.parse_args()

    metrics = run_sensitivity(args)
    METRICS.parent.mkdir(parents=True, exist_ok=True)
    METRICS.write_text(json.dumps(metrics, indent=2, sort_keys=True) + "\n")

    high_low = metrics["aggregate_verdicts"]["high_vs_low"]
    rmt = metrics["aggregate_verdicts"]["rmt_controls"]
    print(f"sensitivity metrics written to {project_rel(METRICS)}")
    print(f"sensitivity summary written to {project_rel(SUMMARY_CSV)}")
    print(
        "high-vs-low: "
        f"{high_low['high_lt_low_count']}/{high_low['total_configurations']} configurations have high RMS residual < low"
    )
    print(
        "GUE-vs-Poisson: "
        f"{rmt['gue_lt_poisson_count']}/{rmt['total_comparisons']} comparisons have GUE RMS residual < Poisson"
    )
    for path in metrics["figures"]:
        print(f"figure written: {path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
