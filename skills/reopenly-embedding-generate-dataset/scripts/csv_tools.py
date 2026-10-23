#!/usr/bin/env python3
"""Inspect document-chunk CSVs and finalize LLM-generated embedding triplets."""

import argparse
import csv
import json
import os
import sys
import tempfile
from pathlib import Path


def fail(message):
    print(f"Error: {message}", file=sys.stderr)
    raise SystemExit(1)


def read_records(path, column):
    try:
        stream = path.open("r", encoding="utf-8-sig", newline="")
    except OSError as exc:
        fail(f"Could not open CSV file {path}: {exc}")
    try:
        with stream:
            reader = csv.DictReader(stream)
            if not reader.fieldnames:
                fail("CSV must have a header row.")
            if reader.fieldnames.count(column) != 1:
                fail(f"Expected exactly one {column!r} column. Available columns: {', '.join(reader.fieldnames)}")
            for data_row, row in enumerate(reader, start=1):
                chunk = row.get(column)
                if chunk is None:
                    fail(f"CSV record {data_row} has no value for column {column!r}.")
                yield data_row, chunk
    except (UnicodeDecodeError, csv.Error) as exc:
        fail(f"Could not parse CSV file: {exc}")


def inspect(args):
    path = Path(args.file)
    if not path.is_file():
        fail(f"CSV file not found: {path}")
    total = 0
    chunks = 0
    blank = 0
    for _, chunk in read_records(path, args.column):
        total += 1
        if chunk.strip():
            chunks += 1
        else:
            blank += 1
    size_bytes = path.stat().st_size
    print(json.dumps({
        "file": str(path),
        "size_bytes": size_bytes,
        "size_human": format_size(size_bytes),
        "data_rows": total,
        "document_chunks": chunks,
        "blank_rows_skipped": blank,
        "questions_to_generate": chunks,
    }, indent=2, ensure_ascii=False))


def format_size(size):
    amount = float(size)
    for unit in ("B", "KiB", "MiB", "GiB", "TiB"):
        if amount < 1024 or unit == "TiB":
            return f"{int(amount)} {unit}" if unit == "B" else f"{amount:.2f} {unit}"
        amount /= 1024


def load_generated(path):
    generated = {}
    try:
        with path.open("r", encoding="utf-8", newline="") as stream:
            for line_number, line in enumerate(stream, start=1):
                if not line.strip():
                    continue
                try:
                    row = json.loads(line)
                except json.JSONDecodeError as exc:
                    fail(f"Invalid JSON on generated sidecar line {line_number}: {exc}")
                if not isinstance(row, dict):
                    fail(f"Generated sidecar line {line_number} must contain a JSON object.")
                data_row = row.get("data_row")
                if not isinstance(data_row, int) or isinstance(data_row, bool) or data_row < 1:
                    fail(f"Generated sidecar line {line_number} needs a positive integer data_row.")
                if data_row in generated:
                    fail(f"Generated sidecar contains duplicate data_row {data_row}.")
                for key in ("anchor", "negative"):
                    if not isinstance(row.get(key), str) or not row[key].strip():
                        fail(f"Generated sidecar line {line_number} needs a non-empty string {key!r}.")
                generated[data_row] = (row["anchor"], row["negative"])
    except OSError as exc:
        fail(f"Could not read generated sidecar {path}: {exc}")
    return generated


def finalize(args):
    source = Path(args.file)
    generated_path = Path(args.generated)
    output = Path(args.output)
    if not source.is_file():
        fail(f"CSV file not found: {source}")
    if not generated_path.is_file():
        fail(f"Generated sidecar not found: {generated_path}")
    if output.resolve() in (source.resolve(), generated_path.resolve()):
        fail("Output path must differ from the source CSV and generated sidecar.")
    if output.exists() and not args.overwrite:
        fail(f"Output file already exists: {output} (use --overwrite only with user approval).")

    generated = load_generated(generated_path)
    chunks = {
        data_row: chunk
        for data_row, chunk in read_records(source, args.column)
        if chunk.strip()
    }
    missing = sorted(set(chunks) - set(generated))
    extra = sorted(set(generated) - set(chunks))
    if missing or extra:
        parts = []
        if missing:
            parts.append(f"missing generated records: {missing[:20]}")
        if extra:
            parts.append(f"generated records without non-empty source chunks: {extra[:20]}")
        fail("Generated sidecar does not match the source CSV (" + "; ".join(parts) + ").")

    output.parent.mkdir(parents=True, exist_ok=True)
    temp_path = None
    try:
        with tempfile.NamedTemporaryFile(
            mode="w", encoding="utf-8", newline="", dir=output.parent,
            prefix=f".{output.name}.", suffix=".tmp", delete=False,
        ) as stream:
            temp_path = Path(stream.name)
            writer = csv.DictWriter(stream, fieldnames=("anchor", "positive", "negative"))
            writer.writeheader()
            for data_row in sorted(chunks):
                anchor, negative = generated[data_row]
                writer.writerow({"anchor": anchor, "positive": chunks[data_row], "negative": negative})
        if output.exists() and not args.overwrite:
            fail(f"Output file already exists: {output} (use --overwrite only with user approval).")
        os.replace(temp_path, output)
    except OSError as exc:
        fail(f"Could not write output CSV {output}: {exc}")
    finally:
        if temp_path and temp_path.exists():
            temp_path.unlink()
    print(json.dumps({"output": str(output), "rows": len(chunks)}, indent=2, ensure_ascii=False))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)
    p = sub.add_parser("inspect", help="Count CSV document chunks and report file size")
    p.add_argument("--file", required=True)
    p.add_argument("--column", required=True, help="Column containing document chunks")
    p.set_defaults(func=inspect)
    p = sub.add_parser("finalize", help="Create the embedding-pairs CSV from generated JSONL")
    p.add_argument("--file", required=True, help="Source CSV")
    p.add_argument("--column", required=True, help="Column containing document chunks")
    p.add_argument("--generated", required=True, help="JSONL with data_row, anchor, and negative")
    p.add_argument("--output", required=True)
    p.add_argument("--overwrite", action="store_true", help="Overwrite an existing output (requires user approval)")
    p.set_defaults(func=finalize)
    args = parser.parse_args()
    args.func(args)


if __name__ == "__main__":
    main()
