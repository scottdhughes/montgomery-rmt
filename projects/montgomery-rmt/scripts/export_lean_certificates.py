#!/usr/bin/env python3
"""Export Lean-readable Montgomery-RMT finite certificates.

The exporter reads existing local Gate 1 outputs and writes generated Lean data
files plus a JSON provenance manifest. It does not fetch data and does not try
to certify analytic number theory, floating-point arithmetic, or transcendental
sine-kernel evaluation.
"""

from __future__ import annotations

import argparse
import csv
import datetime as dt
import hashlib
import json
import os
import subprocess
import sys
from decimal import Decimal, ROUND_HALF_UP, getcontext
from pathlib import Path
from typing import Any


PROJECT = Path(__file__).resolve().parents[1]
ROOT = PROJECT.parents[1]
LEAN_OUT = ROOT / "lean" / "SpectralBridge" / "MontgomeryRMT" / "Generated"
CERT_DIR = PROJECT / "certificates"
CERT_MANIFEST = CERT_DIR / "lean_certificate_manifest.json"
RESIDUAL_SCALE_NAT = 10**30
RESIDUAL_SCALE_DECIMAL = Decimal(RESIDUAL_SCALE_NAT)

LABEL_IDENTIFIERS = {
    "gate0_default": "Gate0Default",
    "block_1e12_10k": "Block1e12",
    "block_1e21_10k": "Block1e21",
    "gue": "Gue",
    "goe": "Goe",
    "poisson": "Poisson",
}


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


def lean_nat_list(values: list[int], *, per_line: int = 10, indent: str = "  ") -> str:
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


def lean_bool_list(values: list[bool], *, per_line: int = 12, indent: str = "  ") -> str:
    words = ["true" if value else "false" for value in values]
    if not words:
        return "[]"
    chunks = [words[index : index + per_line] for index in range(0, len(words), per_line)]
    if len(chunks) == 1:
        return "[" + ", ".join(chunks[0]) + "]"
    lines: list[str] = []
    for index, chunk in enumerate(chunks):
        prefix = "[" if index == 0 else indent
        suffix = "]" if index == len(chunks) - 1 else ","
        lines.append(prefix + ", ".join(chunk) + suffix)
    return "\n".join(lines)


def lean_hash_records(records: list[dict[str, str]], *, indent: str = "  ") -> str:
    if not records:
        return "[]"
    lines = ["["]
    for index, record in enumerate(records):
        suffix = "," if index + 1 < len(records) else ""
        lines.append(
            f"{indent}{{ path := {lean_string(record['path'])}, "
            f"sha256 := {lean_string(record['sha256'])} }}{suffix}"
        )
    lines.append("]")
    return "\n".join(lines)


def decode_pair_counts(paircorr_path: Path, *, n_points: int, bin_width: Decimal) -> list[int]:
    counts: list[int] = []
    with paircorr_path.open(newline="") as handle:
        for row in csv.DictReader(handle):
            decoded = Decimal(row["density"]) * Decimal(n_points) * bin_width
            rounded = decoded.to_integral_value(rounding=ROUND_HALF_UP)
            counts.append(int(rounded))
    return counts


def residual_score(paircorr_path: Path) -> int:
    total = Decimal(0)
    with paircorr_path.open(newline="") as handle:
        for row in csv.DictReader(handle):
            residual = Decimal(row["density"]) - Decimal(row["sine_kernel"])
            total += residual * residual
    return int((total * RESIDUAL_SCALE_DECIMAL).to_integral_value(rounding=ROUND_HALF_UP))


def count_summary_csv_rows(path: Path) -> int:
    with path.open(newline="") as handle:
        return sum(1 for _row in csv.DictReader(handle))


def load_gate1_count_data(metrics: dict[str, Any]) -> list[dict[str, Any]]:
    bin_width = Decimal(str(metrics["histogram_parameters"]["bin_width"]))
    k_max = int(metrics["histogram_parameters"]["max_k"])
    rows: list[dict[str, Any]] = []
    for entry in metrics["entries"]:
        label = str(entry["label"])
        paircorr_path = project_path(str(entry["paircorr_path"]))
        spacing_count = int(entry["spacing"]["count"])
        n_points = spacing_count + 1
        counts = decode_pair_counts(paircorr_path, n_points=n_points, bin_width=bin_width)
        rows.append(
            {
                "label": label,
                "identifier": LABEL_IDENTIFIERS[label],
                "kind": str(entry["kind"]),
                "spacing_count": spacing_count,
                "k_max": k_max,
                "bin_count": int(entry["paircorr"]["bin_count"]),
                "counts": counts,
                "accepted_pair_count": sum(counts),
                "paircorr_path": paircorr_path,
            }
        )
    return rows


def load_residual_data(count_data: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return [
        {
            "label": item["label"],
            "identifier": item["identifier"],
            "bin_count": item["bin_count"],
            "score": residual_score(item["paircorr_path"]),
        }
        for item in count_data
    ]


def sensitivity_vectors(metrics: dict[str, Any]) -> dict[str, list[bool]]:
    aggregate = metrics["aggregate_verdicts"]
    high_vs_low = aggregate["high_vs_low"]
    rmt_controls = aggregate["rmt_controls"]

    primary_high_vs_low = [
        bool(item["high_beats_low"]) for item in high_vs_low["comparisons"]
    ]
    strict_monotone = [
        bool(item["strictly_decreasing"])
        for item in high_vs_low["monotone_trend"]["comparisons"]
    ]
    gue_beats_poisson = [
        bool(item["gue_beats_poisson"]) for item in rmt_controls["comparisons"]
    ]

    grouped: dict[str, dict[str, float]] = {}
    for row in metrics["per_configuration_metrics"]:
        if row.get("kind") != "zeta":
            continue
        source = str(row["source"])
        if source not in {"gate0_default", "block_1e21_10k"}:
            continue
        grouped.setdefault(str(row["config_id"]), {})[source] = float(row["l2_to_sine_kernel"])
    block_1e21_vs_low = [
        grouped[config]["block_1e21_10k"] < grouped[config]["gate0_default"]
        for config in sorted(grouped)
        if {"gate0_default", "block_1e21_10k"} <= set(grouped[config])
    ]

    return {
        "primaryHighVsLow": primary_high_vs_low,
        "block1e21VsLow": block_1e21_vs_low,
        "strictThreeBlockMonotone": strict_monotone,
        "gueBeatsPoisson": gue_beats_poisson,
    }


def render_counts_file(count_data: list[dict[str, Any]]) -> str:
    parts = [
        "import SpectralBridge.MontgomeryRMT.PairCount",
        "",
        "/-!",
        "# Generated Gate 1 Count Data",
        "",
        "Generated by `projects/montgomery-rmt/scripts/export_lean_certificates.py`.",
        "This file contains data records only.",
        "-/",
        "",
        "namespace SpectralBridge",
        "namespace MontgomeryRMT",
        "namespace Generated",
        "",
        "structure GeneratedPairHistogramData where",
        "  label : String",
        "  spacingCount : Nat",
        "  kMax : Nat",
        "  binCount : Nat",
        "  counts : List Nat",
        "  acceptedPairCount : Nat",
        "",
    ]
    for item in count_data:
        name = f"gate1Generated{item['identifier']}Counts"
        parts.extend(
            [
                f"def {name} : GeneratedPairHistogramData where",
                f"  label := {lean_string(item['label'])}",
                f"  spacingCount := {item['spacing_count']}",
                f"  kMax := {item['k_max']}",
                f"  binCount := {item['bin_count']}",
                "  counts :=",
                "    " + lean_nat_list(item["counts"], indent="     "),
                f"  acceptedPairCount := {item['accepted_pair_count']}",
                "",
            ]
        )
    list_names = [f"gate1Generated{item['identifier']}Counts" for item in count_data]
    parts.extend(
        [
            "def gate1GeneratedCountCertificates : List GeneratedPairHistogramData :=",
            "  [" + ", ".join(list_names) + "]",
            "",
            "end Generated",
            "end MontgomeryRMT",
            "end SpectralBridge",
            "",
        ]
    )
    return "\n".join(parts)


def render_residuals_file(residual_data: list[dict[str, Any]]) -> str:
    parts = [
        "/-!",
        "# Generated Gate 1 Residual Data",
        "",
        "Generated by `projects/montgomery-rmt/scripts/export_lean_certificates.py`.",
        "Scores are scaled squared-residual sums from exported CSV decimal columns.",
        "This file contains data records only.",
        "-/",
        "",
        "namespace SpectralBridge",
        "namespace MontgomeryRMT",
        "namespace Generated",
        "",
        "structure GeneratedResidualData where",
        "  label : String",
        "  binCount : Nat",
        "  scale : Nat",
        "  score : Nat",
        "",
        f"def gate1GeneratedResidualScale : Nat := {RESIDUAL_SCALE_NAT}",
        "",
    ]
    for item in residual_data:
        name = f"gate1Generated{item['identifier']}Residual"
        parts.extend(
            [
                f"def {name} : GeneratedResidualData where",
                f"  label := {lean_string(item['label'])}",
                f"  binCount := {item['bin_count']}",
                "  scale := gate1GeneratedResidualScale",
                f"  score := {item['score']}",
                "",
            ]
        )
    list_names = [f"gate1Generated{item['identifier']}Residual" for item in residual_data]
    parts.extend(
        [
            "def gate1GeneratedResidualCertificates : List GeneratedResidualData :=",
            "  [" + ", ".join(list_names) + "]",
            "",
            "end Generated",
            "end MontgomeryRMT",
            "end SpectralBridge",
            "",
        ]
    )
    return "\n".join(parts)


def render_sensitivity_file(vectors: dict[str, list[bool]]) -> str:
    summaries = [
        ("generatedPrimaryHighVsLowSummary", "primary high block beats low", vectors["primaryHighVsLow"]),
        ("generatedBlock1e21VsLowSummary", "block_1e21_10k beats low", vectors["block1e21VsLow"]),
        (
            "generatedStrictThreeBlockMonotoneSummary",
            "strict three-block monotone trend",
            vectors["strictThreeBlockMonotone"],
        ),
        ("generatedGueBeatsPoissonSummary", "GUE beats Poisson", vectors["gueBeatsPoisson"]),
    ]
    parts = [
        "/-!",
        "# Generated Gate 1 Sensitivity Data",
        "",
        "Generated by `projects/montgomery-rmt/scripts/export_lean_certificates.py`.",
        "This file contains data records only.",
        "-/",
        "",
        "namespace SpectralBridge",
        "namespace MontgomeryRMT",
        "namespace Generated",
        "",
        "structure GeneratedBoolVectorData where",
        "  label : String",
        "  values : List Bool",
        "  reportedTrueCount : Nat",
        "  reportedTotal : Nat",
        "",
    ]
    for name, label, values in summaries:
        parts.extend(
            [
                f"def {name} : GeneratedBoolVectorData where",
                f"  label := {lean_string(label)}",
                "  values :=",
                "    " + lean_bool_list(values, indent="     "),
                f"  reportedTrueCount := {sum(1 for value in values if value)}",
                f"  reportedTotal := {len(values)}",
                "",
            ]
        )
    parts.extend(
        [
            "def gate1GeneratedSensitivitySummaries : List GeneratedBoolVectorData :=",
            "  [generatedPrimaryHighVsLowSummary, generatedBlock1e21VsLowSummary,",
            "   generatedStrictThreeBlockMonotoneSummary, generatedGueBeatsPoissonSummary]",
            "",
            "end Generated",
            "end MontgomeryRMT",
            "end SpectralBridge",
            "",
        ]
    )
    return "\n".join(parts)


def render_manifest_file(
    *,
    generated_at: str,
    command: str,
    commit: str,
    source_records: list[dict[str, str]],
    generated_records: list[dict[str, str]],
    summary_csv_rows: int,
) -> str:
    parts = [
        "/-!",
        "# Generated Gate 1 Certificate Manifest",
        "",
        "Generated by `projects/montgomery-rmt/scripts/export_lean_certificates.py`.",
        "This file contains provenance strings only.",
        "-/",
        "",
        "namespace SpectralBridge",
        "namespace MontgomeryRMT",
        "namespace Generated",
        "",
        "structure GeneratedHashRecord where",
        "  path : String",
        "  sha256 : String",
        "",
        f"def generatedCertificateGeneratedAtUtc : String := {lean_string(generated_at)}",
        f"def generatedCertificateCommand : String := {lean_string(command)}",
        f"def generatedCertificateSourceGitCommit : String := {lean_string(commit)}",
        f"def generatedSensitivitySummaryCsvRowCount : Nat := {summary_csv_rows}",
        "",
        "def generatedCertificateSourceHashes : List GeneratedHashRecord :=",
        lean_hash_records(source_records),
        "",
        "def generatedCertificateLeanFileHashes : List GeneratedHashRecord :=",
        lean_hash_records(generated_records),
        "",
        "end Generated",
        "end MontgomeryRMT",
        "end SpectralBridge",
        "",
    ]
    return "\n".join(parts)


def source_record(path: Path) -> dict[str, str]:
    resolved = path.resolve()
    return {
        "path": root_rel(resolved),
        "sha256": sha256(resolved),
    }


def write_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--manifest",
        default=str(CERT_MANIFEST),
        help="output JSON manifest path",
    )
    args = parser.parse_args()

    getcontext().prec = 100

    gate1_metrics_path = PROJECT / "outputs" / "gate1_metrics.json"
    sensitivity_metrics_path = PROJECT / "outputs" / "gate1_sensitivity_metrics.json"
    sensitivity_summary_path = PROJECT / "data" / "processed" / "gate1_sensitivity_summary.csv"
    data_manifest_path = PROJECT / "data" / "manifest.json"
    hashes_path = PROJECT / "outputs" / "hashes.json"

    for required in [
        gate1_metrics_path,
        sensitivity_metrics_path,
        sensitivity_summary_path,
        data_manifest_path,
        hashes_path,
    ]:
        if not required.exists():
            raise SystemExit(f"required input missing: {required.relative_to(PROJECT)}")

    gate1_metrics = load_json(gate1_metrics_path)
    sensitivity_metrics = load_json(sensitivity_metrics_path)
    _data_manifest = load_json(data_manifest_path)
    _hashes = load_json(hashes_path)

    count_data = load_gate1_count_data(gate1_metrics)
    residual_data = load_residual_data(count_data)
    vectors = sensitivity_vectors(sensitivity_metrics)
    summary_csv_rows = count_summary_csv_rows(sensitivity_summary_path)

    generated_at = utc_now()
    command = " ".join(sys.argv)
    commit = git_commit()

    LEAN_OUT.mkdir(parents=True, exist_ok=True)
    generated_paths = {
        "counts": LEAN_OUT / "Gate1GeneratedCounts.lean",
        "residuals": LEAN_OUT / "Gate1GeneratedResiduals.lean",
        "sensitivity": LEAN_OUT / "Gate1GeneratedSensitivity.lean",
        "manifest": LEAN_OUT / "Gate1GeneratedManifest.lean",
    }

    write_text(generated_paths["counts"], render_counts_file(count_data))
    write_text(generated_paths["residuals"], render_residuals_file(residual_data))
    write_text(generated_paths["sensitivity"], render_sensitivity_file(vectors))

    source_paths = [
        Path(__file__).resolve(),
        gate1_metrics_path,
        sensitivity_metrics_path,
        sensitivity_summary_path,
        data_manifest_path,
        hashes_path,
        *(item["paircorr_path"] for item in count_data),
    ]
    source_records = [source_record(path) for path in source_paths]

    preliminary_generated_records = [
        {"path": root_rel(path), "sha256": sha256(path)}
        for key, path in generated_paths.items()
        if key != "manifest"
    ]
    write_text(
        generated_paths["manifest"],
        render_manifest_file(
            generated_at=generated_at,
            command=command,
            commit=commit,
            source_records=source_records,
            generated_records=preliminary_generated_records,
            summary_csv_rows=summary_csv_rows,
        ),
    )

    generated_records = [
        {"path": root_rel(path), "sha256": sha256(path)}
        for path in generated_paths.values()
    ]

    manifest = {
        "generated_at_utc": generated_at,
        "generation_command": command,
        "git_commit": commit,
        "source_inputs": source_records,
        "generated_lean_files": generated_records,
        "summary": {
            "count_certificate_count": len(count_data),
            "residual_certificate_count": len(residual_data),
            "sensitivity_summary_csv_rows": summary_csv_rows,
            "primary_high_vs_low_true_count": sum(vectors["primaryHighVsLow"]),
            "block_1e21_vs_low_true_count": sum(vectors["block1e21VsLow"]),
            "strict_three_block_monotone_true_count": sum(vectors["strictThreeBlockMonotone"]),
            "gue_beats_poisson_true_count": sum(vectors["gueBeatsPoisson"]),
            "gue_beats_poisson_total": len(vectors["gueBeatsPoisson"]),
        },
        "boundary": {
            "certifies": "finite generated count, residual-score, sensitivity-vector, and provenance data",
            "does_not_certify": [
                "Odlyzko ordinates are zeta zeros",
                "raw floating-point arithmetic",
                "transcendental sine-kernel evaluation",
                "Riemann hypothesis",
                "Montgomery pair correlation",
                "GUE limits",
                "physics claims",
            ],
        },
    }

    manifest_path = Path(args.manifest)
    if not manifest_path.is_absolute():
        manifest_path = PROJECT / manifest_path
    manifest_path.parent.mkdir(parents=True, exist_ok=True)
    manifest_path.write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8")

    print(f"generated Lean certificates: {LEAN_OUT.relative_to(ROOT)}")
    for path in generated_paths.values():
        print(f"- {root_rel(path)}")
    print(f"certificate manifest: {root_rel(manifest_path)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
