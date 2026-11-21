#!/usr/bin/env python3
"""Import embedding training pairs from CSV into a ReOpenly embedding dataset."""

import argparse
import csv
import hashlib
import json
import os
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
import uuid
from pathlib import Path

API_ORIGIN = "https://reopenly.com"
REQUIRED_COLUMNS = ("anchor", "positive", "negative")


def fail(message):
    print(f"Error: {message}", file=sys.stderr)
    raise SystemExit(1)


def project_path(args, suffix=""):
    owner = urllib.parse.quote(args.owner, safe="")
    project = urllib.parse.quote(args.project, safe="")
    base = f"/api/v1/projects/{owner}/{project}"
    return f"{base}/{suffix.lstrip('/')}" if suffix else base


def request(path, method="GET", body=None, content_type="application/json", raw=False):
    key = os.environ.get("REOPENLY_API_KEY")
    if not key:
        fail("Set REOPENLY_API_KEY in the environment before calling ReOpenly.")
    headers = {"Authorization": f"Bearer {key}"}
    data = body
    if isinstance(body, (dict, list)):
        data = json.dumps(body).encode("utf-8")
    if data is not None and content_type:
        headers["Content-Type"] = content_type
    req = urllib.request.Request(API_ORIGIN + path, data=data, headers=headers, method=method)
    try:
        with urllib.request.urlopen(req, timeout=120) as response:
            payload = response.read()
            if raw:
                return payload
            return json.loads(payload) if payload else {}
    except urllib.error.HTTPError as exc:
        detail = exc.read().decode("utf-8", "replace")
        try:
            detail = json.dumps(json.loads(detail), ensure_ascii=False)
        except json.JSONDecodeError:
            pass
        fail(f"ReOpenly returned HTTP {exc.code}: {detail}")
    except urllib.error.URLError as exc:
        fail(f"Could not reach ReOpenly: {exc.reason}")


def upload_file(upload, import_id, dataset_import_path, file_path):
    kind = upload.get("kind")
    if kind == "backend":
        url = API_ORIGIN + dataset_import_path
        method = "PUT"
        headers = dict(upload.get("headers") or {})
        headers["Authorization"] = f"Bearer {os.environ['REOPENLY_API_KEY']}"
    else:
        url = upload.get("url")
        method = upload.get("method", "PUT")
        headers = upload.get("headers") or {}
        if not url:
            fail(f"Import {import_id} did not provide an upload URL.")

    try:
        data = file_path.read_bytes()
        req = urllib.request.Request(url, data=data, headers=headers, method=method)
        with urllib.request.urlopen(req, timeout=120) as response:
            response.read()
    except urllib.error.HTTPError as exc:
        detail = exc.read().decode("utf-8", "replace")
        fail(f"CSV upload returned HTTP {exc.code}: {detail}")
    except (OSError, urllib.error.URLError) as exc:
        fail(f"Could not upload CSV bytes: {exc}")


def validate_csv(path):
    try:
        with path.open("r", encoding="utf-8-sig", newline="") as stream:
            reader = csv.reader(stream)
            headers = next(reader, None)
    except (OSError, UnicodeDecodeError, csv.Error) as exc:
        fail(f"Could not read CSV header: {exc}")
    if not headers:
        fail("CSV must have a header row.")
    duplicates = sorted({name for name in headers if headers.count(name) > 1})
    if duplicates:
        fail(f"CSV contains duplicate column names: {', '.join(duplicates)}")
    missing = [column for column in REQUIRED_COLUMNS if column not in headers]
    if missing:
        fail(f"CSV is missing required columns: {', '.join(missing)}")


def sha256_file(path):
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def import_csv(args):
    file_path = Path(args.file)
    if not file_path.is_file():
        fail(f"CSV file not found: {file_path}")
    validate_csv(file_path)

    project = request(project_path(args))
    if project.get("type") != "embedding":
        fail(f"Project {args.owner}/{args.project} has type {project.get('type')!r}; this skill only supports embedding projects.")

    dataset_id = urllib.parse.quote(args.dataset_id, safe="")
    dataset_import_path = project_path(args, f"datasets/{dataset_id}/imports")
    created = request(dataset_import_path, "POST", {
        "filename": file_path.name,
        "size_bytes": file_path.stat().st_size,
    })
    import_id = created.get("id")
    upload = created.get("upload")
    if import_id is None or not isinstance(upload, dict):
        fail(f"Import creation response was missing an import id or upload details: {json.dumps(created)}")

    quoted_import_id = urllib.parse.quote(str(import_id), safe="")
    import_path = project_path(args, f"imports/{quoted_import_id}")
    content_path = project_path(args, f"imports/{quoted_import_id}/content")
    print(f"Created import {import_id}; uploading CSV...", flush=True)
    upload_file(upload, import_id, content_path, file_path)

    profile = request(import_path + "/profile", "POST", {})
    expected_sha256 = profile.get("sha256")
    if not expected_sha256:
        fail(f"Import profiling did not return a SHA-256 digest: {json.dumps(profile)}")
    preview_sha256 = sha256_file(file_path)
    if expected_sha256 != preview_sha256:
        fail("The profiled import digest does not match the local CSV; refusing to confirm changed content.")
    mapping = {column: column for column in REQUIRED_COLUMNS}
    policy = "fail"
    request(import_path + "/preview", "POST", {
        "mapping": mapping,
        "invalid_row_policy": policy,
    })
    print("Import preview passed; confirming import...", flush=True)

    confirmation = request(import_path + "/confirm", "POST", {
        "mapping": mapping,
        "invalid_row_policy": policy,
        "expected_sha256": expected_sha256,
        "idempotency_key": str(uuid.uuid4()),
    })
    print(f"Import {import_id} confirmed; waiting for completion...", flush=True)
    status = confirmation
    while status.get("status") not in ("succeeded", "failed", "cancelled"):
        time.sleep(args.poll_seconds)
        status = request(import_path)
    print(json.dumps(status, indent=2, ensure_ascii=False))
    if status.get("status") != "succeeded":
        fail(f"Import {import_id} ended with status {status.get('status')}.")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)
    p = sub.add_parser("csv", help="Import embedding anchor/positive/negative pairs from CSV")
    p.add_argument("--owner", required=True, help="ReOpenly account/owner slug")
    p.add_argument("--project", required=True, help="Embedding project slug")
    p.add_argument("--dataset-id", required=True, help="Target embedding dataset ID")
    p.add_argument("--file", required=True, help="CSV with anchor, positive, and negative columns")
    p.add_argument("--poll-seconds", type=int, default=5)
    p.set_defaults(func=import_csv)
    args = parser.parse_args()
    if args.poll_seconds < 1:
        fail("--poll-seconds must be at least 1.")
    args.func(args)


if __name__ == "__main__":
    main()
