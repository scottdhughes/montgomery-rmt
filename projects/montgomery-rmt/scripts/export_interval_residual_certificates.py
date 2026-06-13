#!/usr/bin/env python3
"""Export Arb-backed interval residual certificates for Montgomery-RMT.

This optional lane uses python-flint/Arb to enclose the sine-kernel values at
the default Gate 1 bin centers. It then combines those enclosures with exact
integer histogram counts recovered from existing pair-correlation CSVs and
exports Lean-readable rational interval certificates.

If python-flint is not installed, the script reports SKIP and writes no files.
The normal project build must not depend on this optional dependency.
"""

from __future__ import annotations

import argparse
import csv
import datetime as dt
import hashlib
import importlib.metadata
import json
import os
import subprocess
import sys
from dataclasses import dataclass
from decimal import Decimal, ROUND_HALF_UP
from fractions import Fraction
from pathlib import Path
from typing import Any


PROJECT = Path(__file__).resolve().parents[1]
ROOT = PROJECT.parents[1]
LEAN_ROOT = ROOT / "lean" / "SpectralBridge" / "MontgomeryRMT"
LEAN_OUT = LEAN_ROOT / "Generated"
CERT_MANIFEST = PROJECT / "certificates" / "lean_certificate_manifest.json"

DEFAULT_BLOCKS = ["gate0_default", "block_1e12_10k", "block_1e21_10k"]
LABEL_IDENTIFIERS = {
    "gate0_default": "Gate0Default",
    "block_1e12_10k": "Block1e12",
    "block_1e21_10k": "Block1e21",
}


@dataclass(frozen=True)
class SineInterval:
    index: int
    center_num: int
    center_den: int
    lower: int
    upper: int


@dataclass(frozen=True)
class ResidualInterval:
    label: str
    identifier: str
    spacing_count: int
    bin_count: int
    counts: list[int]
    lower: int
    upper: int
    denominator: int


def utc_now() -> str:
    fixed = os.environ.get("SPECTRAL_BRIDGE_TIMESTAMP")
    if fixed:
        return fixed
    return dt.datetime.now(dt.UTC).replace(microsecond=0).isoformat()


def root_rel(path: Path) -> str:
    return str(path.resolve().relative_to(ROOT.resolve()))


def project_rel(path: Path) -> str:
    return str(path.resolve().relative_to(PROJECT.resolve()))


def project_path(text: str) -> Path:
    path = Path(text)
    return path if path.is_absolute() else PROJECT / path


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text())


def git_commit() -> str:
    fixed = os.environ.get("SPECTRAL_BRIDGE_SOURCE_COMMIT")
    if fixed:
        return fixed
    try:
        return subprocess.check_output(
            ["git", "rev-parse", "HEAD"],
            cwd=ROOT,
            text=True,
            stderr=subprocess.DEVNULL,
        ).strip()
    except (subprocess.CalledProcessError, FileNotFoundError):
        return "unknown"


def lean_string(text: str) -> str:
    return json.dumps(text)


def lean_nat_list(values: list[int], *, per_line: int = 8, indent: str = "  ") -> str:
    if not values:
        return "[]"
    chunks = [values[index : index + per_line] for index in range(0, len(values), per_line)]
    if len(chunks) == 1:
        return "[" + ", ".join(str(value) for value in chunks[0]) + "]"
    lines: list[str] = []
    for index, chunk in enumerate(chunks):
        prefix = "[" if index == 0 else indent
        suffix = "]" if index == len(chunks) - 1 else ","
        lines.append(prefix + ", ".join(str(value) for value in chunk) + suffix)
    return "\n".join(lines)


def parse_blocks(text: str) -> list[str]:
    blocks = [item.strip() for item in text.split(",") if item.strip()]
    if not blocks:
        raise SystemExit("at least one block is required")
    unknown = [block for block in blocks if block not in LABEL_IDENTIFIERS]
    if unknown:
        raise SystemExit(f"unsupported interval-certificate block(s): {', '.join(unknown)}")
    return blocks


def require_flint() -> tuple[Any, Any, str] | None:
    try:
        from flint import arb, ctx
    except ModuleNotFoundError:
        return None
    try:
        version = importlib.metadata.version("python-flint")
    except importlib.metadata.PackageNotFoundError:
        version = "unknown"
    return arb, ctx, version


def decode_pair_counts(paircorr_path: Path, *, n_points: int, bin_width: Fraction) -> list[int]:
    counts: list[int] = []
    width_decimal = Decimal(bin_width.numerator) / Decimal(bin_width.denominator)
    with paircorr_path.open(newline="") as handle:
        for row in csv.DictReader(handle):
            decoded = Decimal(row["density"]) * Decimal(n_points) * width_decimal
            rounded = decoded.to_integral_value(rounding=ROUND_HALF_UP)
            counts.append(int(rounded))
    return counts


def load_block_entries(metrics: dict[str, Any], blocks: list[str]) -> list[dict[str, Any]]:
    by_label = {str(entry["label"]): entry for entry in metrics["entries"]}
    missing = [block for block in blocks if block not in by_label]
    if missing:
        raise SystemExit(f"missing Gate 1 metric entries: {', '.join(missing)}")
    return [by_label[block] for block in blocks]


def scaled_floor(arb_value: Any, scale: int) -> int:
    return int((arb_value.lower() * scale).floor().unique_fmpz())


def scaled_ceil(arb_value: Any, scale: int) -> int:
    return int((arb_value.upper() * scale).ceil().unique_fmpz())


def sine_kernel_intervals(
    *,
    arb: Any,
    bin_count: int,
    bin_width: Fraction,
    scale: int,
) -> list[SineInterval]:
    intervals: list[SineInterval] = []
    for index in range(bin_count):
        center = Fraction(2 * index + 1, 2) * bin_width
        u = arb(center.numerator) / center.denominator
        x = arb.pi() * u
        value = arb(1) - (x.sin() / x) ** 2
        lower = scaled_floor(value, scale)
        upper = scaled_ceil(value, scale)
        if lower < 0 or upper < lower:
            raise SystemExit(
                f"invalid sine-kernel interval at bin {index}: [{lower}, {upper}]"
            )
        intervals.append(
            SineInterval(
                index=index,
                center_num=center.numerator,
                center_den=center.denominator,
                lower=lower,
                upper=upper,
            )
        )
    return intervals


def residual_interval(
    *,
    entry: dict[str, Any],
    intervals: list[SineInterval],
    bin_width: Fraction,
    sine_scale: int,
) -> ResidualInterval:
    label = str(entry["label"])
    spacing_count = int(entry["spacing"]["count"])
    n_points = spacing_count + 1
    paircorr_path = project_path(str(entry["paircorr_path"]))
    counts = decode_pair_counts(paircorr_path, n_points=n_points, bin_width=bin_width)
    if len(counts) != len(intervals):
        raise SystemExit(
            f"bin count mismatch for {label}: {len(counts)} counts, "
            f"{len(intervals)} sine intervals"
        )

    density_den = n_points * bin_width.numerator
    denominator = (density_den * sine_scale) ** 2
    lower_total = 0
    upper_total = 0
    for count, interval in zip(counts, intervals):
        density_num = count * bin_width.denominator
        lower_diff = density_num * sine_scale - interval.upper * density_den
        upper_diff = density_num * sine_scale - interval.lower * density_den
        if lower_diff > upper_diff:
            raise SystemExit(f"invalid residual difference interval for {label}")
        if lower_diff <= 0 <= upper_diff:
            lower_square = 0
        else:
            lower_square = min(lower_diff * lower_diff, upper_diff * upper_diff)
        upper_square = max(lower_diff * lower_diff, upper_diff * upper_diff)
        lower_total += lower_square
        upper_total += upper_square

    return ResidualInterval(
        label=label,
        identifier=LABEL_IDENTIFIERS[label],
        spacing_count=spacing_count,
        bin_count=len(counts),
        counts=counts,
        lower=lower_total,
        upper=upper_total,
        denominator=denominator,
    )


def render_sine_intervals_file(
    *,
    generated_at: str,
    command: str,
    python_flint_version: str,
    precision_dps: int,
    precision_bits: int,
    bin_width: Fraction,
    u_max: Fraction,
    intervals: list[SineInterval],
    sine_scale: int,
) -> str:
    parts = [
        "/-!",
        "# Generated Gate 1 Sine-Kernel Intervals",
        "",
        "Generated by `projects/montgomery-rmt/scripts/export_interval_residual_certificates.py`.",
        "The interval endpoints are rational numbers encoded as natural-number",
        "numerators over the common scale `gate1SineKernelIntervalScale`.",
        "-/",
        "",
        "namespace SpectralBridge",
        "namespace MontgomeryRMT",
        "namespace Generated",
        "",
        "structure SineKernelInterval where",
        "  binIndex : Nat",
        "  centerNum : Nat",
        "  centerDen : Nat",
        "  lower : Nat",
        "  upper : Nat",
        "  scale : Nat",
        "deriving DecidableEq, Repr",
        "",
        f"def gate1IntervalGeneratedAtUtc : String := {lean_string(generated_at)}",
        f"def gate1IntervalGenerationCommand : String := {lean_string(command)}",
        f"def gate1IntervalPythonFlintVersion : String := {lean_string(python_flint_version)}",
        f"def gate1IntervalPrecisionDps : Nat := {precision_dps}",
        f"def gate1IntervalPrecisionBits : Nat := {precision_bits}",
        f"def gate1SineKernelIntervalScale : Nat := {sine_scale}",
        f"def gate1IntervalBinWidthNum : Nat := {bin_width.numerator}",
        f"def gate1IntervalBinWidthDen : Nat := {bin_width.denominator}",
        f"def gate1IntervalUMaxNum : Nat := {u_max.numerator}",
        f"def gate1IntervalUMaxDen : Nat := {u_max.denominator}",
        f"def gate1IntervalBinCount : Nat := {len(intervals)}",
        "",
    ]
    for interval in intervals:
        parts.extend(
            [
                f"def gate1SineKernelInterval{interval.index} : SineKernelInterval where",
                f"  binIndex := {interval.index}",
                f"  centerNum := {interval.center_num}",
                f"  centerDen := {interval.center_den}",
                f"  lower := {interval.lower}",
                f"  upper := {interval.upper}",
                "  scale := gate1SineKernelIntervalScale",
                "",
            ]
        )
    names = [f"gate1SineKernelInterval{interval.index}" for interval in intervals]
    parts.extend(
        [
            "def gate1SineKernelIntervals : List SineKernelInterval :=",
            "  " + "[" + ", ".join(names) + "]",
            "",
            "def sineKernelIntervalWellFormed (interval : SineKernelInterval) : Bool :=",
            "  (decide (interval.centerDen > 0)) &&",
            "  (decide (interval.scale > 0)) &&",
            "  (decide (interval.lower <= interval.upper))",
            "",
            "def gate1SineKernelIntervalsWellFormed : Bool :=",
            "  gate1SineKernelIntervals.all sineKernelIntervalWellFormed",
            "",
            "end Generated",
            "end MontgomeryRMT",
            "end SpectralBridge",
            "",
        ]
    )
    return "\n".join(parts)


def render_residuals_file(
    *,
    residuals: list[ResidualInterval],
    max_k: int,
) -> str:
    parts = [
        "import SpectralBridge.MontgomeryRMT.Generated.Gate1SineKernelIntervals",
        "",
        "/-!",
        "# Generated Gate 1 Interval Residual Bounds",
        "",
        "Generated by `projects/montgomery-rmt/scripts/export_interval_residual_certificates.py`.",
        "Residual bounds are squared-residual sums over the default 100 bins.",
        "-/",
        "",
        "namespace SpectralBridge",
        "namespace MontgomeryRMT",
        "namespace Generated",
        "",
        "structure IntervalResidualData where",
        "  label : String",
        "  spacingCount : Nat",
        "  kMax : Nat",
        "  binCount : Nat",
        "  counts : List Nat",
        "  lower : Nat",
        "  upper : Nat",
        "  denominator : Nat",
        "deriving DecidableEq, Repr",
        "",
    ]
    for residual in residuals:
        name = f"gate1Interval{residual.identifier}Residual"
        parts.extend(
            [
                f"def {name} : IntervalResidualData where",
                f"  label := {lean_string(residual.label)}",
                f"  spacingCount := {residual.spacing_count}",
                f"  kMax := {max_k}",
                f"  binCount := {residual.bin_count}",
                "  counts :=",
                "    " + lean_nat_list(residual.counts, indent="     "),
                f"  lower := {residual.lower}",
                f"  upper := {residual.upper}",
                f"  denominator := {residual.denominator}",
                "",
            ]
        )
    names = [f"gate1Interval{residual.identifier}Residual" for residual in residuals]
    parts.extend(
        [
            "def gate1IntervalResidualCertificates : List IntervalResidualData :=",
            "  [" + ", ".join(names) + "]",
            "",
            "def intervalResidualWellFormed (residual : IntervalResidualData) : Bool :=",
            "  (decide (residual.denominator > 0)) &&",
            "  (decide (residual.lower <= residual.upper)) &&",
            "  (decide (residual.counts.length = residual.binCount))",
            "",
            "def gate1IntervalResidualsWellFormed : Bool :=",
            "  gate1IntervalResidualCertificates.all intervalResidualWellFormed",
            "",
            "end Generated",
            "end MontgomeryRMT",
            "end SpectralBridge",
            "",
        ]
    )
    return "\n".join(parts)


def source_record(path: Path) -> dict[str, str]:
    resolved = path.resolve()
    return {
        "path": root_rel(resolved),
        "sha256": sha256(resolved),
    }


def generated_record(path: Path) -> dict[str, str]:
    return {
        "path": root_rel(path),
        "sha256": sha256(path),
    }


def write_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def update_manifest(
    *,
    generated_at: str,
    command: str,
    commit: str,
    python_flint_version: str,
    precision_dps: int,
    precision_bits: int,
    sine_scale: int,
    source_paths: list[Path],
    generated_paths: list[Path],
    residuals: list[ResidualInterval],
) -> None:
    manifest = load_json(CERT_MANIFEST) if CERT_MANIFEST.exists() else {}
    manifest["interval_residual_certificate"] = {
        "generated_at_utc": generated_at,
        "generation_command": command,
        "git_commit": commit,
        "python_flint_version": python_flint_version,
        "precision_dps": precision_dps,
        "precision_bits": precision_bits,
        "sine_kernel_interval_scale": sine_scale,
        "source_inputs": [source_record(path) for path in source_paths],
        "generated_lean_files": [generated_record(path) for path in generated_paths],
        "summary": {
            "blocks": [residual.label for residual in residuals],
            "bin_count": residuals[0].bin_count if residuals else 0,
            "gate0_lower_gt_block_1e12_upper": (
                residuals[0].lower > residuals[1].upper if len(residuals) > 1 else False
            ),
            "block_1e12_lower_gt_block_1e21_upper": (
                residuals[1].lower > residuals[2].upper if len(residuals) > 2 else False
            ),
        },
        "boundary": {
            "certifies": (
                "finite squared-residual ordering from exported histogram counts "
                "and Arb-backed sine-kernel interval enclosures"
            ),
            "does_not_certify": [
                "Odlyzko ordinates are zeta zeros",
                "raw floating-point arithmetic",
                "Riemann hypothesis",
                "Montgomery pair correlation",
                "GUE limits",
                "physics claims",
            ],
        },
    }
    CERT_MANIFEST.parent.mkdir(parents=True, exist_ok=True)
    CERT_MANIFEST.write_text(
        json.dumps(manifest, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )


def main() -> int:
    parser = argparse.ArgumentParser()
    precision = parser.add_mutually_exclusive_group()
    precision.add_argument("--dps", type=int, default=100, help="Arb decimal precision")
    precision.add_argument("--bits", type=int, help="Arb bit precision")
    parser.add_argument("--u-max", type=str, default="5.0")
    parser.add_argument("--bin-width", type=str, default="0.05")
    parser.add_argument("--max-k", type=int, default=50)
    parser.add_argument("--blocks", default=",".join(DEFAULT_BLOCKS))
    args = parser.parse_args()

    flint_state = require_flint()
    if flint_state is None:
        print(
            "SKIP interval residual certificates: python-flint/Arb is not "
            "available in this Python environment."
        )
        print("No generated Lean interval certificate files were written.")
        return 0
    arb, ctx, python_flint_version = flint_state

    if args.bits is not None:
        ctx.prec = args.bits
    else:
        ctx.dps = args.dps
    precision_dps = int(ctx.dps)
    precision_bits = int(ctx.prec)

    blocks = parse_blocks(args.blocks)
    bin_width = Fraction(args.bin_width)
    u_max = Fraction(args.u_max)
    if bin_width <= 0 or u_max <= 0:
        raise SystemExit("--bin-width and --u-max must be positive")
    bin_count_fraction = u_max / bin_width
    if bin_count_fraction.denominator != 1:
        raise SystemExit("--u-max must be an integer multiple of --bin-width")
    bin_count = bin_count_fraction.numerator

    gate1_metrics_path = PROJECT / "outputs" / "gate1_metrics.json"
    if not gate1_metrics_path.exists():
        raise SystemExit(f"required input missing: {project_rel(gate1_metrics_path)}")
    metrics = load_json(gate1_metrics_path)
    params = metrics.get("histogram_parameters", {})
    if Fraction(str(params.get("bin_width"))) != bin_width:
        raise SystemExit("requested bin width does not match Gate 1 metrics")
    if Fraction(str(params.get("u_max"))) != u_max:
        raise SystemExit("requested u_max does not match Gate 1 metrics")
    if int(params.get("max_k")) != args.max_k:
        raise SystemExit("requested max_k does not match Gate 1 metrics")

    scale_digits = max(20, precision_dps - 20)
    sine_scale = 10**scale_digits
    intervals = sine_kernel_intervals(
        arb=arb,
        bin_count=bin_count,
        bin_width=bin_width,
        scale=sine_scale,
    )

    entries = load_block_entries(metrics, blocks)
    residuals = [
        residual_interval(
            entry=entry,
            intervals=intervals,
            bin_width=bin_width,
            sine_scale=sine_scale,
        )
        for entry in entries
    ]
    denominators = {residual.denominator for residual in residuals}
    if len(denominators) != 1:
        raise SystemExit("default interval residual denominators are not common")
    if len(residuals) >= 3 and not (
        residuals[0].lower > residuals[1].upper
        and residuals[1].lower > residuals[2].upper
    ):
        raise SystemExit("interval residual bounds do not prove the default chain")

    generated_at = utc_now()
    command = " ".join(sys.argv)
    commit = git_commit()

    LEAN_OUT.mkdir(parents=True, exist_ok=True)
    sine_path = LEAN_OUT / "Gate1SineKernelIntervals.lean"
    residual_path = LEAN_OUT / "Gate1IntervalResiduals.lean"
    generated_paths = [sine_path, residual_path]
    write_text(
        sine_path,
        render_sine_intervals_file(
            generated_at=generated_at,
            command=command,
            python_flint_version=python_flint_version,
            precision_dps=precision_dps,
            precision_bits=precision_bits,
            bin_width=bin_width,
            u_max=u_max,
            intervals=intervals,
            sine_scale=sine_scale,
        ),
    )
    write_text(
        residual_path,
        render_residuals_file(
            residuals=residuals,
            max_k=args.max_k,
        ),
    )

    source_paths = [
        Path(__file__).resolve(),
        gate1_metrics_path,
        *(project_path(str(entry["paircorr_path"])) for entry in entries),
    ]
    update_manifest(
        generated_at=generated_at,
        command=command,
        commit=commit,
        python_flint_version=python_flint_version,
        precision_dps=precision_dps,
        precision_bits=precision_bits,
        sine_scale=sine_scale,
        source_paths=source_paths,
        generated_paths=generated_paths,
        residuals=residuals,
    )

    print(f"generated interval residual certificates: {LEAN_OUT.relative_to(ROOT)}")
    for path in generated_paths:
        print(f"- {root_rel(path)}")
    print(f"certificate manifest updated: {root_rel(CERT_MANIFEST)}")
    print(
        "interval chain: "
        f"{residuals[0].label}.lower > {residuals[1].label}.upper and "
        f"{residuals[1].label}.lower > {residuals[2].label}.upper"
    )
    print(f"python-flint: {python_flint_version}; Arb precision: {precision_dps} dps / {precision_bits} bits")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
