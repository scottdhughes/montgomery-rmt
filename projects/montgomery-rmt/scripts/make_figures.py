#!/usr/bin/env python3
"""Generate Montgomery-RMT Gate 0 figures."""

from __future__ import annotations

import argparse
import csv
import html
import math
import os
from pathlib import Path
from typing import Sequence

PROJECT = Path(__file__).resolve().parents[1]
ROOT = PROJECT.parents[1]
PROCESSED = PROJECT / "data" / "processed"
FIGURES = PROJECT / "outputs" / "figures"
FIGURE_NAMES = [
    "zeta_spacing",
    "zeta_paircorr",
    "gue_spacing",
    "poisson_control",
    "zeta_vs_gue_vs_poisson_paircorr",
]

for cache_dir in [ROOT / ".matplotlib", ROOT / ".cache"]:
    cache_dir.mkdir(parents=True, exist_ok=True)

os.environ.setdefault("MPLBACKEND", "Agg")
os.environ.setdefault("MPLCONFIGDIR", str(ROOT / ".matplotlib"))
os.environ.setdefault("XDG_CACHE_HOME", str(ROOT / ".cache"))

try:
    import matplotlib.pyplot as plt

    HAS_MATPLOTLIB = True
except ModuleNotFoundError:
    plt = None
    HAS_MATPLOTLIB = False


def read_column(path: Path, column: str) -> list[float]:
    values: list[float] = []
    with path.open(newline="") as handle:
        reader = csv.DictReader(handle)
        for row in reader:
            try:
                values.append(float(row[column]))
            except (KeyError, TypeError, ValueError):
                continue
    return values


def read_paircorr(path: Path) -> tuple[list[float], list[float], list[float]]:
    centers: list[float] = []
    density: list[float] = []
    sine: list[float] = []
    with path.open(newline="") as handle:
        reader = csv.DictReader(handle)
        for row in reader:
            centers.append(float(row["bin_center"]))
            density.append(float(row["density"]))
            sine.append(float(row["sine_kernel"]))
    return centers, density, sine


def clear_previous_figures() -> None:
    FIGURES.mkdir(parents=True, exist_ok=True)
    for name in FIGURE_NAMES:
        for suffix in [".png", ".svg"]:
            path = FIGURES / f"{name}{suffix}"
            if path.exists():
                path.unlink()


def points_to_polyline(points: Sequence[tuple[float, float]]) -> str:
    return " ".join(f"{x:.2f},{y:.2f}" for x, y in points)


def write_svg(path: Path, body: str, title: str, width: int = 960, height: int = 540) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    escaped_title = html.escape(title)
    svg = f"""<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" viewBox="0 0 {width} {height}">
  <title>{escaped_title}</title>
  <rect width="100%" height="100%" fill="#ffffff"/>
  <text x="48" y="42" font-family="Arial, sans-serif" font-size="22" fill="#111111">{escaped_title}</text>
{body}
</svg>
"""
    path.write_text(svg)


def save_spacing_svg(spacings: Sequence[float], title: str, output: Path) -> Path:
    output = output.with_suffix(".svg")
    values = [value for value in spacings if math.isfinite(value)]
    if not values:
        raise ValueError("cannot plot spacing figure without finite spacing values")

    bin_count = 60
    x_min = min(values)
    x_max = max(values)
    if x_min == x_max:
        x_min -= 0.5
        x_max += 0.5
    width = (x_max - x_min) / bin_count
    counts = [0] * bin_count
    for value in values:
        index = min(bin_count - 1, max(0, int((value - x_min) / width)))
        counts[index] += 1
    densities = [count / (len(values) * width) for count in counts]
    y_max = max(densities) or 1.0

    left, top, chart_w, chart_h = 70, 74, 830, 380
    bar_w = chart_w / bin_count
    bars: list[str] = []
    for index, density in enumerate(densities):
        x = left + index * bar_w
        h = chart_h * density / y_max
        y = top + chart_h - h
        bars.append(
            f'  <rect x="{x:.2f}" y="{y:.2f}" width="{max(bar_w - 1, 1):.2f}" height="{h:.2f}" fill="#4f6f8f" opacity="0.76"/>'
        )

    body = "\n".join(
        [
            f'  <line x1="{left}" y1="{top + chart_h}" x2="{left + chart_w}" y2="{top + chart_h}" stroke="#111111"/>',
            f'  <line x1="{left}" y1="{top}" x2="{left}" y2="{top + chart_h}" stroke="#111111"/>',
            *bars,
            f'  <text x="{left + chart_w / 2:.2f}" y="506" text-anchor="middle" font-family="Arial, sans-serif" font-size="15" fill="#222222">normalized nearest-neighbor spacing</text>',
            '  <text x="24" y="270" transform="rotate(-90 24 270)" text-anchor="middle" font-family="Arial, sans-serif" font-size="15" fill="#222222">density</text>',
            f'  <text x="{left}" y="482" font-family="Arial, sans-serif" font-size="12" fill="#333333">{x_min:.3g}</text>',
            f'  <text x="{left + chart_w}" y="482" text-anchor="end" font-family="Arial, sans-serif" font-size="12" fill="#333333">{x_max:.3g}</text>',
            f'  <text x="{left - 8}" y="{top + 4}" text-anchor="end" font-family="Arial, sans-serif" font-size="12" fill="#333333">{y_max:.3g}</text>',
        ]
    )
    write_svg(output, body, title + " (finite numerical evidence)")
    return output


def scale_line(
    xs: Sequence[float],
    ys: Sequence[float],
    *,
    x_min: float,
    x_max: float,
    y_min: float,
    y_max: float,
    left: int,
    top: int,
    chart_w: int,
    chart_h: int,
) -> list[tuple[float, float]]:
    x_span = x_max - x_min or 1.0
    y_span = y_max - y_min or 1.0
    points: list[tuple[float, float]] = []
    for x, y in zip(xs, ys, strict=False):
        if not (math.isfinite(x) and math.isfinite(y)):
            continue
        px = left + chart_w * (x - x_min) / x_span
        py = top + chart_h - chart_h * (y - y_min) / y_span
        points.append((px, py))
    return points


def save_lines_svg(series: Sequence[tuple[str, Sequence[float], Sequence[float], str]], title: str, output: Path) -> Path:
    output = output.with_suffix(".svg")
    all_x = [x for _, xs, _, _ in series for x in xs if math.isfinite(x)]
    all_y = [y for _, _, ys, _ in series for y in ys if math.isfinite(y)]
    if not all_x or not all_y:
        raise ValueError("cannot plot line figure without finite data")

    x_min, x_max = min(all_x), max(all_x)
    y_min, y_max = min(0.0, min(all_y)), max(all_y)
    if y_min == y_max:
        y_max = y_min + 1.0

    left, top, chart_w, chart_h = 70, 74, 830, 380
    lines: list[str] = [
        f'  <line x1="{left}" y1="{top + chart_h}" x2="{left + chart_w}" y2="{top + chart_h}" stroke="#111111"/>',
        f'  <line x1="{left}" y1="{top}" x2="{left}" y2="{top + chart_h}" stroke="#111111"/>',
    ]
    legend_y = top + 18
    for index, (label, xs, ys, color) in enumerate(series):
        points = scale_line(
            xs,
            ys,
            x_min=x_min,
            x_max=x_max,
            y_min=y_min,
            y_max=y_max,
            left=left,
            top=top,
            chart_w=chart_w,
            chart_h=chart_h,
        )
        if points:
            lines.append(
                f'  <polyline points="{points_to_polyline(points)}" fill="none" stroke="{color}" stroke-width="2.4"/>'
            )
        ly = legend_y + index * 22
        lines.append(f'  <line x1="738" y1="{ly}" x2="778" y2="{ly}" stroke="{color}" stroke-width="2.4"/>')
        lines.append(
            f'  <text x="786" y="{ly + 5}" font-family="Arial, sans-serif" font-size="13" fill="#222222">{html.escape(label)}</text>'
        )

    lines.extend(
        [
            f'  <text x="{left + chart_w / 2:.2f}" y="506" text-anchor="middle" font-family="Arial, sans-serif" font-size="15" fill="#222222">u</text>',
            '  <text x="24" y="270" transform="rotate(-90 24 270)" text-anchor="middle" font-family="Arial, sans-serif" font-size="15" fill="#222222">density</text>',
            f'  <text x="{left}" y="482" font-family="Arial, sans-serif" font-size="12" fill="#333333">{x_min:.3g}</text>',
            f'  <text x="{left + chart_w}" y="482" text-anchor="end" font-family="Arial, sans-serif" font-size="12" fill="#333333">{x_max:.3g}</text>',
            f'  <text x="{left - 8}" y="{top + 4}" text-anchor="end" font-family="Arial, sans-serif" font-size="12" fill="#333333">{y_max:.3g}</text>',
        ]
    )
    write_svg(output, "\n".join(lines), title + " (finite numerical evidence)")
    return output


def save_spacing_figure(spacings: Sequence[float], title: str, output: Path) -> Path:
    if not HAS_MATPLOTLIB:
        return save_spacing_svg(spacings, title, output)
    assert plt is not None
    plt.figure()
    plt.hist(spacings, bins=60, density=True, alpha=0.75, label="finite spacing histogram")
    plt.title(title + " (finite numerical evidence)")
    plt.xlabel("normalized nearest-neighbor spacing")
    plt.ylabel("density")
    plt.legend()
    plt.tight_layout()
    output.parent.mkdir(parents=True, exist_ok=True)
    plt.savefig(output, dpi=160)
    plt.close()
    return output


def save_paircorr_figure(path: Path, title: str, output: Path) -> Path:
    centers, density, sine = read_paircorr(path)
    if not HAS_MATPLOTLIB:
        return save_lines_svg(
            [
                ("finite pair-correlation histogram", centers, density, "#4f6f8f"),
                ("sine-kernel reference", centers, sine, "#b54a4a"),
            ],
            title,
            output,
        )
    assert plt is not None
    plt.figure()
    plt.plot(centers, density, label="finite pair-correlation histogram")
    plt.plot(centers, sine, label="sine-kernel reference")
    plt.title(title + " (finite numerical evidence)")
    plt.xlabel("u")
    plt.ylabel("density")
    plt.legend()
    plt.tight_layout()
    output.parent.mkdir(parents=True, exist_ok=True)
    plt.savefig(output, dpi=160)
    plt.close()
    return output


def save_comparison(output: Path) -> Path:
    series: list[tuple[str, list[float], list[float], str]] = []
    sine_series: tuple[list[float], list[float]] | None = None
    colors = {"zeta": "#4f6f8f", "GUE": "#558b6e", "Poisson": "#b65f4b"}
    for label, filename in [
        ("zeta", "zeta_paircorr.csv"),
        ("GUE", "gue_paircorr.csv"),
        ("Poisson", "poisson_paircorr.csv"),
    ]:
        centers, density, sine = read_paircorr(PROCESSED / filename)
        series.append((label, centers, density, colors[label]))
        sine_series = (centers, sine)
    if sine_series is not None:
        series.append(("sine-kernel reference", sine_series[0], sine_series[1], "#111111"))
    if not HAS_MATPLOTLIB:
        return save_lines_svg(series, "Zeta vs GUE vs Poisson pair correlation", output)
    assert plt is not None
    plt.figure()
    for label, centers, density, _color in series[:-1]:
        plt.plot(centers, density, label=label)
    centers, sine = sine_series if sine_series is not None else ([], [])
    plt.plot(centers, sine, label="sine-kernel reference", linestyle="--")
    plt.title("Zeta vs GUE vs Poisson pair correlation (finite numerical evidence)")
    plt.xlabel("u")
    plt.ylabel("density")
    plt.legend()
    plt.tight_layout()
    output.parent.mkdir(parents=True, exist_ok=True)
    plt.savefig(output, dpi=160)
    plt.close()
    return output


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.parse_args()

    clear_previous_figures()
    written = [
        save_spacing_figure(
            read_column(PROCESSED / "zeta_spacings.csv", "spacing_normalized"),
            "Zeta zero spacing",
            FIGURES / "zeta_spacing.png",
        ),
        save_paircorr_figure(
            PROCESSED / "zeta_paircorr.csv",
            "Zeta pair correlation",
            FIGURES / "zeta_paircorr.png",
        ),
        save_spacing_figure(
            read_column(PROCESSED / "gue_spacings.csv", "spacing_normalized"),
            "GUE spacing",
            FIGURES / "gue_spacing.png",
        ),
        save_spacing_figure(
            read_column(PROCESSED / "poisson_spacings.csv", "spacing_normalized"),
            "Poisson negative control",
            FIGURES / "poisson_control.png",
        ),
        save_comparison(FIGURES / "zeta_vs_gue_vs_poisson_paircorr.png"),
    ]
    backend = "matplotlib" if HAS_MATPLOTLIB else "stdlib-svg"
    print(f"figures written to {FIGURES.relative_to(PROJECT)} using {backend}")
    for path in written:
        print(f"- {path.relative_to(PROJECT)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
