#!/usr/bin/env python3
"""Lightweight source-package audit for the Montgomery-RMT paper."""

from __future__ import annotations

import argparse
import re
from dataclasses import dataclass
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]


@dataclass(frozen=True)
class Finding:
    level: str
    message: str


def read(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def bib_keys(text: str) -> set[str]:
    return set(re.findall(r"@\w+\s*\{\s*([^,\s]+)", text))


def cite_keys(text: str) -> set[str]:
    keys: set[str] = set()
    for body in re.findall(r"\\cite\{([^}]+)\}", text):
        for key in body.split(","):
            key = key.strip()
            if key:
                keys.add(key)
    return keys


def figure_paths(text: str) -> list[tuple[str, bool]]:
    paths: list[tuple[str, bool]] = []
    for path in re.findall(r"\\FigureOrPlaceholder\{([^}]+)\}", text):
        paths.append((path, True))
    for path in re.findall(r"\\includegraphics(?:\[[^\]]*\])?\{([^}]+)\}", text):
        if path == "#1":
            continue
        paths.append((path, False))
    return paths


def is_negative_context(line: str) -> bool:
    lowered = line.lower()
    negative_markers = (
        "no ",
        "not ",
        "does not",
        "do not",
        "without",
        "not be read",
        "not a proof",
    )
    return any(marker in lowered for marker in negative_markers)


def source_files(root: Path) -> list[Path]:
    paths: list[Path] = []
    for pattern in ("paper/*.tex", "paper/*.bib", "paper/*.bbl"):
        paths.extend(sorted(root.glob(pattern)))
    return paths


PUBLIC_FORBIDDEN_TERMS = (
    "Aris" + "totle",
    "Phys" + "lib",
    "Lane" + " A",
    "internal" + " lane",
    "theorem" + "-shape scaffolding",
)


def public_forbidden_findings(root: Path) -> list[Finding]:
    findings: list[Finding] = []
    for path in source_files(root):
        label = str(path.relative_to(root))
        text = read(path)
        for line_no, line in enumerate(text.splitlines(), start=1):
            for term in PUBLIC_FORBIDDEN_TERMS:
                if re.search(re.escape(term), line, flags=re.IGNORECASE):
                    findings.append(
                        Finding(
                            "ERROR",
                            f"{label}:{line_no} contains public-package internal term: {term}",
                        )
                    )
    return findings


def generated_data_findings(root: Path) -> list[Finding]:
    findings: list[Finding] = []
    forbidden_parts = {
        "__pycache__",
        ".venv",
        ".lake",
        "external",
        "raw",
        "processed",
    }
    forbidden_suffixes = {".csv", ".json", ".pyc"}
    for path in sorted(item for item in root.rglob("*") if item.is_file()):
        rel = path.relative_to(root)
        parts = set(rel.parts)
        if any(part in forbidden_parts for part in parts):
            findings.append(Finding("ERROR", f"Generated or external artifact included: {rel}"))
            continue
        if path.name.endswith(".sage.py") or path.suffix.lower() in forbidden_suffixes:
            findings.append(Finding("ERROR", f"Generated data/cache file included: {rel}"))
            continue
        if rel.parts[:1] == ("outputs",) and rel.parts[:2] != ("outputs", "figures"):
            findings.append(Finding("ERROR", f"Non-figure output included: {rel}"))
            continue
        if " " in str(rel):
            findings.append(Finding("ERROR", f"Package filename contains a space: {rel}"))
    return findings


def audit(root: Path, *, package_mode: bool) -> tuple[str, int, list[Finding]]:
    findings: list[Finding] = []
    paper_dir = root / "paper"
    main_tex = paper_dir / "main.tex"
    refs_bib = paper_dir / "refs.bib"
    main_bbl = paper_dir / "main.bbl"

    if not main_tex.exists():
        findings.append(Finding("ERROR", "Missing paper/main.tex."))
        return "RED", 1, findings

    tex = read(main_tex)
    bib = read(refs_bib) if refs_bib.exists() else ""
    findings.extend(public_forbidden_findings(root))

    checked_sources = source_files(root)
    if not checked_sources:
        checked_sources = [main_tex]
    for path in checked_sources:
        label = str(path.relative_to(root))
        text = read(path)
        local_path_pattern = "/" + "Users/|" + "/" + "private/|" + "/" + "Volumes/"
        if re.search(local_path_pattern, text):
            findings.append(Finding("ERROR", f"{label} contains a local absolute path."))

    if r"\date{\today}" in tex:
        findings.append(Finding("WARN", r"main.tex uses \date{\today}; use a fixed date before posting."))

    if package_mode:
        if not refs_bib.exists() and not main_bbl.exists():
            findings.append(Finding("ERROR", "Package must include paper/refs.bib or paper/main.bbl."))
        findings.extend(generated_data_findings(root))

    for path_text, protected in figure_paths(tex):
        if " " in path_text:
            findings.append(Finding("ERROR", f"Figure path contains a space: {path_text}"))
        if not re.fullmatch(r"[A-Za-z0-9_./-]+", path_text):
            findings.append(Finding("WARN", f"Figure path has a non-portable character: {path_text}"))
        candidate = (paper_dir / path_text).resolve()
        try:
            candidate.relative_to(root.resolve())
        except ValueError:
            findings.append(Finding("WARN", f"Figure path resolves outside project root: {path_text}"))
        if not candidate.exists():
            level = "ERROR" if package_mode or not protected else "WARN"
            detail = "protected by \\IfFileExists" if protected else "unprotected"
            findings.append(Finding(level, f"Missing figure file ({detail}): {path_text}"))
        elif package_mode and candidate.suffix.lower() not in {".png", ".pdf", ".jpg", ".jpeg"}:
            findings.append(Finding("ERROR", f"Figure format may not be arXiv-compatible: {path_text}"))

    if refs_bib.exists():
        cited = cite_keys(tex)
        available = bib_keys(bib)
        missing = sorted(cited - available)
        unused = sorted(available - cited)
        for key in missing:
            findings.append(Finding("ERROR", f"Citation key missing from refs.bib: {key}"))
        for key in unused:
            findings.append(Finding("WARN", f"refs.bib key is unused by main.tex: {key}"))

    overclaim_phrases = (
        "we prove",
        "we proved",
        "proof of RH",
        "proof of Montgomery",
        "solves",
        "breakthrough",
        "physical Hamiltonian",
        "confirms",
        "verifies",
        "establishes",
        "settles",
    )
    for line_no, line in enumerate(tex.splitlines(), start=1):
        lowered = line.lower()
        for phrase in overclaim_phrases:
            if phrase.lower() in lowered and not is_negative_context(line):
                findings.append(Finding("ERROR", f"Potential overclaim at main.tex:{line_no}: {phrase}"))

    if any(f.level == "ERROR" for f in findings):
        verdict = "RED"
        exit_code = 1
    elif findings:
        verdict = "YELLOW"
        exit_code = 0
    else:
        verdict = "GREEN"
        exit_code = 0

    return verdict, exit_code, findings


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--package-dir",
        type=Path,
        help="Audit an assembled package directory instead of the repository paper source.",
    )
    args = parser.parse_args()

    root = args.package_dir.resolve() if args.package_dir else PROJECT_ROOT
    package_mode = args.package_dir is not None
    verdict, exit_code, findings = audit(root, package_mode=package_mode)

    print(f"{verdict}: Montgomery-RMT paper package audit")
    if package_mode:
        print(f"Package directory: {root}")
        print(f"Compile check: run from package root with `latexmk -pdf paper/main.tex`.")
    if findings:
        for finding in findings:
            print(f"{finding.level}: {finding.message}")
    else:
        print("No actionable source-package findings.")
    return exit_code


if __name__ == "__main__":
    raise SystemExit(main())
