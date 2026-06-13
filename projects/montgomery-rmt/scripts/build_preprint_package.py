#!/usr/bin/env python3
"""Build a minimal Montgomery-RMT preprint source package."""

from __future__ import annotations

import argparse
import re
import shutil
import tarfile
from dataclasses import dataclass
from pathlib import Path


PROJECT = Path(__file__).resolve().parents[1]
PAPER_DIR = PROJECT / "paper"
MAIN_TEX = PAPER_DIR / "main.tex"
REFS_BIB = PAPER_DIR / "refs.bib"
DEFAULT_PACKAGE_DIR = PROJECT / "dist" / "preprint_package"
DEFAULT_TARBALL = PROJECT / "dist" / "montgomery_rmt_preprint_source.tar.gz"


@dataclass(frozen=True)
class CopyItem:
    source: Path
    destination: Path


def read(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def project_rel(path: Path) -> str:
    return str(path.relative_to(PROJECT))


def figure_paths(tex: str) -> list[str]:
    paths: list[str] = []
    for path in re.findall(r"\\FigureOrPlaceholder\{([^}]+)\}", tex):
        paths.append(path)
    for path in re.findall(r"\\includegraphics(?:\[[^\]]*\])?\{([^}]+)\}", tex):
        if path != "#1":
            paths.append(path)
    return sorted(set(paths))


def resolve_paper_path(path_text: str) -> Path:
    if " " in path_text:
        raise SystemExit(f"referenced figure path contains a space: {path_text}")
    if not re.fullmatch(r"[A-Za-z0-9_./-]+", path_text):
        raise SystemExit(f"referenced figure path is not portable: {path_text}")
    source = (PAPER_DIR / path_text).resolve()
    try:
        source.relative_to(PROJECT.resolve())
    except ValueError as exc:
        raise SystemExit(f"referenced figure resolves outside project root: {path_text}") from exc
    if source.suffix.lower() != ".png":
        raise SystemExit(f"preprint package expected PNG figure, got: {path_text}")
    if not source.exists():
        raise SystemExit(f"referenced figure is missing: {path_text}")
    return source


def collect_items() -> list[CopyItem]:
    if not MAIN_TEX.exists():
        raise SystemExit(f"missing source: {project_rel(MAIN_TEX)}")
    if not REFS_BIB.exists():
        raise SystemExit(f"missing bibliography: {project_rel(REFS_BIB)}")

    items = [
        CopyItem(MAIN_TEX, Path("paper") / "main.tex"),
        CopyItem(REFS_BIB, Path("paper") / "refs.bib"),
    ]
    for path_text in figure_paths(read(MAIN_TEX)):
        source = resolve_paper_path(path_text)
        items.append(CopyItem(source, source.relative_to(PROJECT)))
    return sorted(items, key=lambda item: str(item.destination))


def ensure_under_project_dist(path: Path) -> Path:
    resolved = path.resolve()
    dist = (PROJECT / "dist").resolve()
    try:
        resolved.relative_to(dist)
    except ValueError as exc:
        raise SystemExit(f"refusing to write outside project dist directory: {path}") from exc
    return resolved


def write_package(package_dir: Path, items: list[CopyItem]) -> None:
    package_dir = ensure_under_project_dist(package_dir)
    if package_dir.exists():
        shutil.rmtree(package_dir)
    package_dir.mkdir(parents=True, exist_ok=True)
    for item in items:
        destination = package_dir / item.destination
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(item.source, destination)


def write_tarball(package_dir: Path, tarball: Path) -> None:
    package_dir = ensure_under_project_dist(package_dir)
    tarball = ensure_under_project_dist(tarball)
    tarball.parent.mkdir(parents=True, exist_ok=True)
    if tarball.exists():
        tarball.unlink()
    with tarfile.open(tarball, "w:gz") as archive:
        archive.add(package_dir, arcname=package_dir.name)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--package-dir", type=Path, default=DEFAULT_PACKAGE_DIR)
    parser.add_argument("--tarball", type=Path, default=DEFAULT_TARBALL)
    parser.add_argument("--no-tarball", action="store_true")
    args = parser.parse_args()

    items = collect_items()
    write_package(args.package_dir, items)
    if not args.no_tarball:
        write_tarball(args.package_dir, args.tarball)

    print(f"preprint package written: {project_rel(args.package_dir.resolve())}")
    print("copied files:")
    for item in items:
        print(f"- {item.destination}")
    if not args.no_tarball:
        print(f"tarball written: {project_rel(args.tarball.resolve())}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
