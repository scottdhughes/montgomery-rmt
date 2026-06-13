#!/usr/bin/env python3
"""Explicit Odlyzko block fetch and normalization for Montgomery-RMT Gate 1."""

from __future__ import annotations

import argparse
import csv
import datetime as dt
import gzip
import hashlib
import json
import platform
import sys
import urllib.error
import urllib.request
from decimal import Decimal, InvalidOperation
from pathlib import Path
from typing import Any, Iterable


PROJECT = Path(__file__).resolve().parents[1]
BLOCKS_PATH = PROJECT / "data" / "odlyzko_blocks.json"
MANIFEST = PROJECT / "data" / "manifest.json"
HASHES = PROJECT / "outputs" / "hashes.json"


def utc_now() -> str:
    return dt.datetime.now(dt.UTC).replace(microsecond=0).isoformat()


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def project_path(path_text: str) -> Path:
    path = Path(path_text)
    return path if path.is_absolute() else PROJECT / path


def load_blocks() -> dict[str, dict[str, Any]]:
    data = json.loads(BLOCKS_PATH.read_text())
    return data["blocks"]


def load_json(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    try:
        return json.loads(path.read_text())
    except json.JSONDecodeError:
        return {}


def write_json(path: Path, data: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2, sort_keys=True) + "\n")


def update_hashes(paths: Iterable[Path]) -> dict[str, str]:
    hashes = load_json(HASHES)
    for path in paths:
        hashes[str(path.relative_to(PROJECT))] = sha256(path)
    write_json(HASHES, hashes)
    return hashes


def update_manifest(
    *,
    block_name: str,
    block: dict[str, Any],
    source_path: Path | None,
    output_path: Path,
    row_count: int,
    downloaded: bool,
    used_existing_normalized: bool,
    hashes: dict[str, str],
) -> None:
    manifest = load_json(MANIFEST)
    manifest.setdefault("odlyzko_blocks", {})
    source_hash = hashes.get(str(source_path.relative_to(PROJECT))) if source_path else None
    output_hash = hashes[str(output_path.relative_to(PROJECT))]
    manifest["odlyzko_blocks"][block_name] = {
        "block": block_name,
        "generated_at_utc": utc_now(),
        "description": block.get("description"),
        "zero_index_start": block.get("zero_index_start"),
        "zero_index_end": block.get("zero_index_end"),
        "expected_count": block.get("expected_count"),
        "actual_count": row_count,
        "source_url": block.get("source_url"),
        "source_path": str(source_path.relative_to(PROJECT)) if source_path else None,
        "source_sha256": source_hash,
        "output_path": str(output_path.relative_to(PROJECT)),
        "output_sha256": output_hash,
        "downloaded": downloaded,
        "used_existing_normalized": used_existing_normalized,
        "precision_note": block.get("precision_note"),
        "notes": block.get("notes"),
        "python": sys.version,
        "platform": platform.platform(),
    }
    write_json(MANIFEST, manifest)


def download_block(block: dict[str, Any], destination: Path, timeout: int) -> None:
    destination.parent.mkdir(parents=True, exist_ok=True)
    request = urllib.request.Request(
        str(block["source_url"]),
        headers={"User-Agent": "spectral-bridge-gate1/0.1"},
    )
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            destination.write_bytes(response.read())
    except urllib.error.URLError as exc:
        raise RuntimeError(f"download failed for {block['label']}: {exc}") from exc


def numeric_lines(path: Path) -> Iterable[str]:
    opener = gzip.open if path.suffix == ".gz" else open
    with opener(path, "rt", encoding="utf-8", errors="replace") as handle:
        for line in handle:
            token = line.strip().replace(",", "")
            if not token:
                continue
            try:
                Decimal(token)
            except InvalidOperation:
                continue
            yield token


def normalize_source(block_name: str, block: dict[str, Any], source_path: Path, output_path: Path) -> int:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    start_index = int(block["zero_index_start"])
    source = f"odlyzko_{block_name}"
    offset_base = Decimal(str(block["offset_base"])) if "offset_base" in block else None
    row_count = 0
    with output_path.open("w", newline="") as handle:
        writer = csv.DictWriter(
            handle,
            fieldnames=["index", "gamma", "source", "block_label"],
            lineterminator="\n",
        )
        writer.writeheader()
        for row_count, token in enumerate(numeric_lines(source_path), start=1):
            gamma = Decimal(token)
            if offset_base is not None:
                gamma += offset_base
            writer.writerow(
                {
                    "index": start_index + row_count - 1,
                    "gamma": format(gamma, "f"),
                    "source": source,
                    "block_label": block_name,
                }
            )
    expected = block.get("expected_count")
    if expected is not None and row_count != int(expected):
        raise RuntimeError(f"{block_name}: expected {expected} rows, wrote {row_count}")
    return row_count


def count_normalized_csv(path: Path) -> int:
    with path.open(newline="") as handle:
        return max(sum(1 for _ in handle) - 1, 0)


def main() -> int:
    blocks = load_blocks()
    parser = argparse.ArgumentParser()
    parser.add_argument("--block", required=True, choices=sorted(blocks))
    parser.add_argument("--download", action="store_true")
    parser.add_argument("--use-existing", action="store_true")
    parser.add_argument("--timeout", type=int, default=60)
    args = parser.parse_args()

    block = blocks[args.block]
    source_path = project_path(str(block["local_path"]))
    output_path = project_path(str(block["normalized_csv"]))
    downloaded = False
    used_existing_normalized = False

    if args.download:
        print(f"downloading {args.block} from {block['source_url']}")
        download_block(block, source_path, args.timeout)
        downloaded = True

    if source_path.exists():
        row_count = normalize_source(args.block, block, source_path, output_path)
        hash_paths = [source_path, output_path]
    elif output_path.exists():
        row_count = count_normalized_csv(output_path)
        expected = block.get("expected_count")
        if expected is not None and row_count != int(expected):
            raise SystemExit(f"{args.block}: existing normalized CSV has {row_count} rows, expected {expected}")
        hash_paths = [output_path]
        used_existing_normalized = True
    else:
        raise SystemExit(
            f"{args.block}: no local source file at {source_path.relative_to(PROJECT)} and no normalized CSV at "
            f"{output_path.relative_to(PROJECT)}. Re-run with --download to fetch this block explicitly."
        )

    hashes = update_hashes(hash_paths)
    update_manifest(
        block_name=args.block,
        block=block,
        source_path=source_path if source_path.exists() else None,
        output_path=output_path,
        row_count=row_count,
        downloaded=downloaded,
        used_existing_normalized=used_existing_normalized,
        hashes=hashes,
    )
    print(
        f"odlyzko block: block={args.block} rows={row_count} "
        f"output={output_path.relative_to(PROJECT)} sha256={hashes[str(output_path.relative_to(PROJECT))]}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
