#!/usr/bin/env python3
"""Small, dependency-free ReOpenly API client used by the repository skills."""

import argparse
import concurrent.futures
import csv
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


def fail(message):
    print(f"Error: {message}", file=sys.stderr)
    raise SystemExit(1)


def project_path(args, suffix):
    return f"/api/v1/projects/{urllib.parse.quote(args.owner, safe='')}/{urllib.parse.quote(args.project, safe='')}/{suffix.lstrip('/')}"


def request(path, method="GET", body=None, content_type="application/json", extra_headers=None, raw=False):
    key = os.environ.get("REOPENLY_API_KEY")
    if not key:
        fail("Set REOPENLY_API_KEY in the environment before calling ReOpenly.")
    headers = {"Authorization": f"Bearer {key}"}
    data = body
    if isinstance(body, (dict, list)):
        data = json.dumps(body).encode()
    if data is not None:
        headers["Content-Type"] = content_type
    if extra_headers:
        headers.update(extra_headers)
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


def csv_upload(args):
    path = Path(args.file)
    if not path.is_file():
        fail(f"CSV file not found: {path}")
    count = 0
    with path.open("r", encoding="utf-8-sig", newline="") as stream:
        reader = csv.DictReader(stream)
        if not reader.fieldnames:
            fail("CSV must have a header row.")
        for field in (args.question_column, args.answer_column):
            if field not in reader.fieldnames:
                fail(f"CSV column {field!r} is missing. Available columns: {', '.join(reader.fieldnames)}")
        for line, row in enumerate(reader, start=2):
            question = (row.get(args.question_column) or "").strip()
            answer = (row.get(args.answer_column) or "").strip()
            if not question or not answer:
                if args.invalid == "skip":
                    continue
                fail(f"Row {line} has an empty question or answer (use --invalid skip to skip invalid rows).")
            payload = {
                "name": f"{args.name_prefix}-{line-1}",
                "messages": [
                    {"role": "user", "text": question},
                    {"role": "assistant", "text": answer},
                ],
            }
            if args.tag:
                payload["tags"] = args.tag
            request(project_path(args, "chats"), "POST", payload)
            count += 1
            if count % 25 == 0:
                print(f"Uploaded {count} examples...", file=sys.stderr)
    print(json.dumps({"uploaded": count, "project": f"{args.owner}/{args.project}"}, indent=2))


def hf_upload(args):
    try:
        from datasets import load_dataset
    except ImportError:
        fail("Hugging Face import requires the optional package: python -m pip install datasets")
    try:
        dataset = load_dataset(args.dataset, args.config, split=args.split, streaming=args.streaming)
    except Exception as exc:
        fail(f"Could not load Hugging Face dataset: {exc}")
    for col in (args.question_column, args.answer_column):
        if col not in dataset.column_names:
            fail(f"Dataset column {col!r} not found. Available columns: {', '.join(dataset.column_names)}")
    endpoint = project_path(args, "chats")
    count = 0
    completed = 0
    pending = set()

    def upload(payload):
        return request(endpoint, "POST", payload)

    # Keep outstanding work bounded for both regular and streaming datasets.
    with concurrent.futures.ThreadPoolExecutor(max_workers=5) as pool:
        try:
            for index, row in enumerate(dataset):
                question, answer = row.get(args.question_column), row.get(args.answer_column)
                if not isinstance(question, str) or not isinstance(answer, str) or not question.strip() or not answer.strip():
                    if args.invalid == "skip":
                        continue
                    fail(f"Example {index} has a missing or non-text question/answer (use --invalid skip to skip).")
                payload = {
                    "name": f"{args.name_prefix}-{index+1}",
                    "messages": [
                        {"role": "user", "text": question.strip()},
                        {"role": "assistant", "text": answer.strip()},
                    ],
                }
                if args.tag:
                    payload["tags"] = args.tag
                pending.add(pool.submit(upload, payload))
                count += 1
                if args.limit and count >= args.limit:
                    break
                if len(pending) >= 5:
                    done, pending = concurrent.futures.wait(
                        pending, return_when=concurrent.futures.FIRST_COMPLETED
                    )
                    for future in done:
                        future.result()
                        completed += 1
                        if completed % 25 == 0:
                            print(f"Uploaded {completed} examples...", file=sys.stderr)
            for future in concurrent.futures.as_completed(pending):
                future.result()
                completed += 1
                if completed % 25 == 0:
                    print(f"Uploaded {completed} examples...", file=sys.stderr)
        except BaseException:
            for future in pending:
                future.cancel()
            raise
    print(json.dumps({"uploaded": count, "dataset": args.dataset, "split": args.split,
                      "project": f"{args.owner}/{args.project}"}, indent=2))


def train(args):
    if not re.fullmatch(r"[a-z0-9]+(?:-[a-z0-9]+)*", args.model_slug):
        fail("--model-slug must be lowercase kebab-case (letters, digits, hyphens).")
    payload = {"dataset_tags": args.tag or [], "model_name": args.base_model,
               "max_seq_length": args.max_seq_length, "num_train_epochs": args.epochs}
    if args.system_prompt:
        payload["system_prompt"] = args.system_prompt
    if not args.yes:
        print("Training request (training time may incur charges):")
        print(json.dumps(payload, indent=2))
        if input("Create this training job? [y/N] ").strip().lower() not in ("y", "yes"):
            fail("Cancelled; no job was created.")
    created = request(project_path(args, "training-jobs"), "POST", payload)
    job_id = created.get("id")
    if job_id is None:
        print(json.dumps(created, indent=2))
        fail("Training API response did not contain an id; inspect the response and job list before retrying.")
    print(f"Created training job {job_id}. Polling for completion...", flush=True)
    while True:
        job = request(project_path(args, f"training-jobs/{urllib.parse.quote(str(job_id), safe='')}"))
        status = job.get("status", "unknown")
        print(f"Job {job_id}: status={status}, progress={job.get('progress', 'n/a')}, model_available={job.get('model_available', False)}", flush=True)
        if status in ("failed", "cancelled"):
            print(json.dumps(job, indent=2))
            fail(f"Training job ended with status {status}; no model was deployed.")
        if job.get("model_available"):
            break
        if status == "succeeded":
            print(json.dumps(job, indent=2))
            fail("Training job succeeded but has no available model; no alias was deployed.")
        time.sleep(args.poll_seconds)
    if not args.deploy:
        print(json.dumps({"job_id": job_id, "model_available": True}, indent=2))
        return
    model = {"name": args.model_name, "slug": args.model_slug, "training_job_id": job_id}
    if not args.yes:
        print("Deploy hosted-model alias:")
        print(json.dumps(model, indent=2))
        if input("Deploy this model alias? [y/N] ").strip().lower() not in ("y", "yes"):
            print(f"Training finished; deploy later with training job {job_id}.")
            return
    deployed = request(project_path(args, "models"), "POST", model)
    print(json.dumps({"job_id": job_id, "model": deployed}, indent=2))


def infer(args):
    url = (f"/api/projects/{urllib.parse.quote(args.owner, safe='')}/"
           f"{urllib.parse.quote(args.project, safe='')}/openai/v1/chat/completions")
    result = request(url, "POST", {"model": args.model, "messages": [{"role": "user", "content": args.prompt}],
                                    "max_tokens": args.max_tokens, "temperature": args.temperature})
    print(json.dumps(result, indent=2, ensure_ascii=False))


def add_project(p):
    p.add_argument("--owner", required=True, help="ReOpenly account/owner slug")
    p.add_argument("--project", required=True, help="ReOpenly project slug")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)
    p = sub.add_parser("csv", help="Upload question/answer rows from CSV")
    add_project(p); p.add_argument("--file", required=True); p.add_argument("--question-column", default="question")
    p.add_argument("--answer-column", default="answer"); p.add_argument("--tag", action="append", default=[])
    p.add_argument("--name-prefix", default="csv"); p.add_argument("--invalid", choices=("fail", "skip"), default="fail")
    p.set_defaults(func=csv_upload)
    p = sub.add_parser("huggingface", help="Load a Hugging Face dataset and upload question/answer rows")
    add_project(p); p.add_argument("--dataset", required=True); p.add_argument("--config"); p.add_argument("--split", default="train")
    p.add_argument("--question-column", required=True); p.add_argument("--answer-column", required=True)
    p.add_argument("--tag", action="append", default=[]); p.add_argument("--name-prefix", default="hf")
    p.add_argument("--invalid", choices=("fail", "skip"), default="fail"); p.add_argument("--limit", type=int, default=0)
    p.add_argument("--streaming", action="store_true"); p.set_defaults(func=hf_upload)
    p = sub.add_parser("train", help="Train and optionally deploy a model")
    add_project(p); p.add_argument("--base-model", required=True); p.add_argument("--tag", action="append", default=[])
    p.add_argument("--epochs", type=float, default=3); p.add_argument("--max-seq-length", type=int, default=2048)
    p.add_argument("--system-prompt"); p.add_argument("--model-name", default="Fine-tuned model")
    p.add_argument("--model-slug", required=True); p.add_argument("--poll-seconds", type=int, default=20)
    p.add_argument("--deploy", action="store_true", help="Create hosted-model alias after training")
    p.add_argument("--yes", action="store_true", help="Skip confirmation prompts"); p.set_defaults(func=train)
    p = sub.add_parser("infer", help="Run a chat completion")
    add_project(p); p.add_argument("--model", required=True); p.add_argument("--prompt", required=True)
    p.add_argument("--max-tokens", type=int, default=256); p.add_argument("--temperature", type=float, default=0.2)
    p.set_defaults(func=infer)
    args = parser.parse_args()
    args.func(args)


if __name__ == "__main__":
    main()
