#!/usr/bin/env python3
"""Train and optionally deploy an embedding model in ReOpenly."""

import argparse
import json
import os
import re
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

API_ORIGIN = "https://reopenly.com"
MAX_STEPS = 10_000


def fail(message):
    print(f"Error: {message}", file=sys.stderr)
    raise SystemExit(1)


def project_path(args, suffix=""):
    owner = urllib.parse.quote(args.owner, safe="")
    project = urllib.parse.quote(args.project, safe="")
    base = f"/api/v1/projects/{owner}/{project}"
    return f"{base}/{suffix.lstrip('/')}" if suffix else base


def request(path, method="GET", body=None):
    key = os.environ.get("REOPENLY_API_KEY")
    if not key:
        fail("Set REOPENLY_API_KEY in the environment before calling ReOpenly.")
    headers = {"Authorization": f"Bearer {key}"}
    data = None
    if body is not None:
        data = json.dumps(body).encode("utf-8")
        headers["Content-Type"] = "application/json"
    req = urllib.request.Request(API_ORIGIN + path, data=data, headers=headers, method=method)
    try:
        with urllib.request.urlopen(req, timeout=120) as response:
            payload = response.read()
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


def load_settings(path):
    if not path:
        return None
    try:
        value = json.loads(Path(path).read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        fail(f"Could not read settings JSON: {exc}")
    if not isinstance(value, dict):
        fail("Settings JSON must be an object.")
    return value


def training_body(args, max_steps, settings):
    body = {
        "dataset_id": args.dataset_id,
        "base_artifact_id": args.base_artifact_id,
        "max_steps": max_steps,
    }
    if settings:
        body["settings"] = settings
    if args.execution_limit_seconds is not None:
        body["execution_limit_seconds"] = args.execution_limit_seconds
    return body


def train_embedding(args):
    if args.epochs < 1:
        fail("--epochs must be a positive whole number.")
    if args.deploy:
        if not args.model_name:
            fail("--model-name is required with --deploy.")
        if not args.model_slug or not re.fullmatch(r"[a-z0-9]+(?:-[a-z0-9]+)*", args.model_slug):
            fail("--model-slug is required with --deploy and must be lowercase kebab-case.")

    project = request(project_path(args))
    if project.get("type") != "embedding":
        fail(f"Project {args.owner}/{args.project} has type {project.get('type')!r}; this helper only supports embedding projects.")

    profiles = request(project_path(args, "training-jobs/profiles"))
    print("Embedding training profiles (select a supported base artifact ID):")
    print(json.dumps(profiles, indent=2, ensure_ascii=False))
    settings = load_settings(args.settings)
    endpoint = project_path(args, "training-jobs")

    discovery = request(endpoint + "/preview", "POST", training_body(args, MAX_STEPS, settings))
    steps_per_epoch = discovery.get("planned_steps_per_epoch")
    if not isinstance(steps_per_epoch, int) or steps_per_epoch < 1:
        fail(f"Preview did not return a valid planned_steps_per_epoch: {json.dumps(discovery)}")
    max_steps = steps_per_epoch * args.epochs
    if max_steps > MAX_STEPS:
        fail(f"Requested {args.epochs} epochs require {max_steps} steps, above the {MAX_STEPS}-step API preview limit.")

    body = training_body(args, max_steps, settings)
    preview = request(endpoint + "/preview", "POST", body)
    selection_sha256 = preview.get("selection_sha256")
    if not selection_sha256:
        fail(f"Training preview did not return selection_sha256: {json.dumps(preview)}")
    estimate = request(endpoint + "/estimate", "POST", body)

    print("Training preview:")
    print(json.dumps(preview, indent=2, ensure_ascii=False))
    print("Training estimate:")
    print(json.dumps(estimate, indent=2, ensure_ascii=False))
    print(f"Requested workload: {args.epochs} epoch(s), {max_steps} steps.")
    if args.deploy:
        print(f"After training, deploy alias {args.model_name!r} ({args.model_slug}).")
    if not args.yes:
        if input("Start this embedding training job? This may incur charges. [y/N] ").strip().lower() not in ("y", "yes"):
            fail("Cancelled; no training job was created.")

    create_body = dict(body)
    create_body["selection_sha256"] = selection_sha256
    created = request(endpoint, "POST", create_body)
    job_id = created.get("id")
    if job_id is None:
        print(json.dumps(created, indent=2, ensure_ascii=False))
        fail("Training API response did not contain a job id; inspect the job list before attempting another create.")
    print(f"Created embedding training job {job_id}; polling for completion...", flush=True)

    while True:
        job_path = project_path(args, f"training-jobs/{urllib.parse.quote(str(job_id), safe='')}")
        job = request(job_path)
        status = job.get("status", "unknown")
        print(f"Job {job_id}: status={status}, progress={job.get('progress', 'n/a')}, model_available={job.get('model_available', False)}", flush=True)
        if job.get("model_available"):
            break
        if status in ("failed", "cancelled", "paused"):
            print(json.dumps(job, indent=2, ensure_ascii=False))
            fail(f"Training job ended with status {status}; no model was deployed.")
        if status == "succeeded":
            print(json.dumps(job, indent=2, ensure_ascii=False))
            fail("Training job succeeded but has no available model; no alias was deployed.")
        time.sleep(args.poll_seconds)

    if not args.deploy:
        print(json.dumps({"job_id": job_id, "status": job.get("status"),
                          "model_available": True, "cost_credits": job.get("cost_credits")}, indent=2))
        return

    model = {
        "name": args.model_name,
        "slug": args.model_slug,
        "task": "embedding",
        "source": {"kind": "training_job", "training_job_id": job_id},
    }
    if not args.yes:
        print("Embedding hosted-model alias:")
        print(json.dumps(model, indent=2))
        if input("Deploy this model alias? [y/N] ").strip().lower() not in ("y", "yes"):
            print(f"Training completed; deploy later from training job {job_id}.")
            return
    deployed = request(project_path(args, "models"), "POST", model)
    print(json.dumps({"job_id": job_id, "status": job.get("status"),
                      "cost_credits": job.get("cost_credits"), "model": deployed}, indent=2))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)
    p = sub.add_parser("embedding-train", help="Train and optionally deploy an embedding model")
    p.add_argument("--owner", required=True, help="ReOpenly account/owner slug")
    p.add_argument("--project", required=True, help="Embedding project slug")
    p.add_argument("--dataset-id", required=True, help="Embedding dataset ID")
    p.add_argument("--base-artifact-id", required=True, help="Base artifact ID from the project training profiles")
    p.add_argument("--epochs", type=int, default=3, help="Number of full epochs (default: 3)")
    p.add_argument("--settings", help="Path to JSON object with embedding training settings")
    p.add_argument("--execution-limit-seconds", type=int, help="Optional run execution deadline")
    p.add_argument("--poll-seconds", type=int, default=20)
    p.add_argument("--deploy", action="store_true", help="Deploy an embedding hosted-model alias after training")
    p.add_argument("--model-name", help="Hosted model display name (required with --deploy)")
    p.add_argument("--model-slug", help="Hosted model kebab-case alias slug (required with --deploy)")
    p.add_argument("--yes", action="store_true", help="Skip confirmation prompts")
    p.set_defaults(func=train_embedding)
    args = parser.parse_args()
    if args.poll_seconds < 1:
        fail("--poll-seconds must be at least 1.")
    if args.execution_limit_seconds is not None and args.execution_limit_seconds < 5:
        fail("--execution-limit-seconds must be at least 5.")
    args.func(args)


if __name__ == "__main__":
    main()
