#!/usr/bin/env python3
"""Bounded zeta-zero acquisition for Montgomery-RMT Gate 0."""

from __future__ import annotations

import argparse
import csv
import datetime as dt
import hashlib
import json
import os
import platform
import shutil
import subprocess
import sys
from pathlib import Path


PROJECT = Path(__file__).resolve().parents[1]
ROOT = PROJECT.parents[1]
RAW = PROJECT / "data" / "raw"
MANIFEST = PROJECT / "data" / "manifest.json"
HASHES = PROJECT / "outputs" / "hashes.json"
DEFAULT_OUT = RAW / "zeta_zeros.csv"


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def utc_now() -> str:
    return dt.datetime.now(dt.UTC).replace(microsecond=0).isoformat()


def find_sage() -> str | None:
    found = shutil.which("sage")
    if found:
        return found
    fallback = Path("/usr/local/bin/sage")
    if fallback.exists():
        return str(fallback)
    return None


def repo_display(text: str) -> str:
    path = Path(text)
    if not path.is_absolute():
        return text
    try:
        return str(path.relative_to(ROOT))
    except ValueError:
        pass
    try:
        return str(path.resolve().relative_to(ROOT.resolve()))
    except ValueError:
        return text


def display_command(argv: list[str]) -> list[str]:
    return [repo_display(item) for item in argv]


def count_rows(path: Path) -> int:
    with path.open(newline="") as handle:
        return max(sum(1 for _ in handle) - 1, 0)


def write_mpmath_zeros(path: Path, count: int) -> None:
    import mpmath as mp

    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="") as handle:
        writer = csv.writer(handle, lineterminator="\n")
        writer.writerow(["index", "gamma", "source"])
        for index in range(1, count + 1):
            zero = mp.zetazero(index)
            writer.writerow([index, mp.nstr(mp.im(zero), 30), "mpmath_zetazero"])


def load_hashes() -> dict[str, str]:
    if HASHES.exists():
        try:
            return json.loads(HASHES.read_text())
        except json.JSONDecodeError:
            return {}
    return {}


def save_hash(path: Path, digest: str) -> None:
    HASHES.parent.mkdir(parents=True, exist_ok=True)
    hashes = load_hashes()
    hashes[str(path.relative_to(PROJECT))] = digest
    HASHES.write_text(json.dumps(hashes, indent=2, sort_keys=True) + "\n")


def try_sage(sage_path: str, n: int, out: Path, timeout: int) -> tuple[bool, str]:
    script = PROJECT / "scripts" / "sage_zeta_zeros.sage"
    env = os.environ.copy()
    env.setdefault("DOT_SAGE", str(ROOT / ".sage"))
    command = [sage_path, str(script), "--n", str(n), "--out", str(out)]
    try:
        result = subprocess.run(
            command,
            capture_output=True,
            text=True,
            timeout=timeout,
            check=False,
            env=env,
        )
    except subprocess.TimeoutExpired:
        return False, f"Sage timed out after {timeout} seconds"

    if result.returncode != 0:
        message = (result.stderr or result.stdout or "").strip()
        return False, message or f"Sage exited with {result.returncode}"
    return True, ""


def write_manifest(
    *,
    requested_n: int,
    actual_n: int,
    source: str,
    sage_path: str | None,
    sage_timeout: int,
    fallback_used: bool,
    precision_note: str,
    command: list[str],
    output_path: Path,
    digest: str,
    failure_note: str,
) -> None:
    existing: dict[str, object] = {}
    if MANIFEST.exists():
        try:
            existing = json.loads(MANIFEST.read_text())
        except json.JSONDecodeError:
            existing = {}
    manifest = {
        "project": "montgomery-rmt",
        "generated_at_utc": utc_now(),
        "requested_n": requested_n,
        "actual_n": actual_n,
        "source": source,
        "sage_path": sage_path,
        "sage_timeout_seconds": sage_timeout,
        "fallback_used": fallback_used,
        "precision_note": precision_note,
        "command": command,
        "output_path": str(output_path.relative_to(PROJECT)),
        "sha256": digest,
        "failure_note": failure_note,
        "python": sys.version,
        "platform": platform.platform(),
    }
    if "odlyzko_blocks" in existing:
        manifest["odlyzko_blocks"] = existing["odlyzko_blocks"]
    MANIFEST.parent.mkdir(parents=True, exist_ok=True)
    MANIFEST.write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--n", type=int, default=10000)
    parser.add_argument("--fallback-n", type=int, default=1000)
    parser.add_argument("--sage-timeout", type=int, default=60)
    parser.add_argument("--out", default=str(DEFAULT_OUT))
    args = parser.parse_args()

    output = Path(args.out)
    if not output.is_absolute():
        output = PROJECT / output
    output.parent.mkdir(parents=True, exist_ok=True)

    sage_path = find_sage()
    fallback_used = False
    failure_note = ""
    requested_n = args.n
    command = display_command(sys.argv[:])

    if sage_path:
        ok, failure_note = try_sage(sage_path, args.n, output, args.sage_timeout)
    else:
        ok = False
        failure_note = "Sage executable not found"

    if ok:
        source = "sage_odlyzko_zeta"
        precision_note = (
            "Sage optional Odlyzko zeta database contains the first 2,001,052 "
            "zero ordinates with documented accuracy about 4e-9."
        )
    else:
        fallback_used = True
        fallback_n = min(args.fallback_n, args.n)
        write_mpmath_zeros(output, fallback_n)
        source = "mpmath_zetazero"
        precision_note = (
            "mpmath fallback computes a small numerical dataset and is not a "
            "substitute for Odlyzko-table provenance."
        )

    actual_n = count_rows(output)
    digest = sha256(output)
    save_hash(output, digest)
    write_manifest(
        requested_n=requested_n,
        actual_n=actual_n,
        source=source,
        sage_path=sage_path,
        sage_timeout=args.sage_timeout,
        fallback_used=fallback_used,
        precision_note=precision_note,
        command=command,
        output_path=output,
        digest=digest,
        failure_note=failure_note,
    )
    print(f"zeta zeros: source={source} count={actual_n} sha256={digest}")
    if failure_note and fallback_used:
        print(f"fallback reason: {failure_note}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
