#!/usr/bin/env python
"""B2.4 + B3 Reader end-to-end smoke — runs ONLY against localhost with in-process dispatcher.

Renamed intentionally **not**: keeping ``try_b2_4_end_to_end.py`` avoids breaking existing docs and
muscle memory; this script now waits long enough for the extra Reader phase (B3).

Usage (token from env, fresh experiment):
    $env:FIVVLE_TEST_TOKEN = (uv run python scripts/_get_token.py)
    uv run python scripts/try_b2_4_end_to_end.py

Usage (token from env, existing REFINED experiment — saves refinement LLM cost):
    $env:FIVVLE_TEST_TOKEN = (uv run python scripts/_get_token.py)
    uv run python scripts/try_b2_4_end_to_end.py <experiment_uuid>

Prerequisites:
    - FastAPI server running locally: uv run uvicorn app.main:app --reload
    - DISPATCHER_MODE=in_process (default)
    - FIVVLE_TEST_TOKEN set (see _get_token.py — requires TEST_EMAIL + TEST_PASSWORD)

DO NOT run this against staging/production.
"""

from __future__ import annotations

import json
import os
import sys
import time
from datetime import UTC, datetime

import httpx

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

BASE_URL = "http://localhost:8000"

# Token sourced from env var — set via:
#   $env:FIVVLE_TEST_TOKEN = (uv run python scripts/_get_token.py)
FIREBASE_ID_TOKEN = os.environ.get("FIVVLE_TEST_TOKEN", "REPLACE_ME")

RAW_IDEA = (
    "A B2B SaaS platform that helps e-commerce brands automatically detect "
    "and recover abandoned checkout sessions using AI-written personalised "
    "follow-up emails, SMS, and WhatsApp nudges. The platform integrates with "
    "Shopify, WooCommerce, and BigCommerce, charges a flat monthly fee plus a "
    "small revenue-share on recovered orders, and targets brands doing "
    "$50k–$2M GMV per month who cannot afford dedicated retention teams."
)
POLL_INTERVAL_SECONDS = 8
MAX_POLLS = 90  # safety cap (~12 min); loop exits early on terminal status

_TERMINAL_STATUSES = frozenset({"RESEARCH_READY", "RESEARCH_FAILED"})

# ---------------------------------------------------------------------------
# Helper
# ---------------------------------------------------------------------------

HEADERS = {"Authorization": f"Bearer {FIREBASE_ID_TOKEN}"}


def log(msg: str, **fields: object) -> None:
    ts = time.strftime("%H:%M:%S")
    parts = " ".join(f"{k}={v!r}" for k, v in fields.items())
    print(f"[{ts}][smoke] {msg} {parts}".strip(), flush=True)


def check_token() -> None:
    if FIREBASE_ID_TOKEN == "REPLACE_ME":
        print(
            "ERROR: Set FIVVLE_TEST_TOKEN before running:\n"
            "  $env:TEST_EMAIL='fivvleio@gmail.com'\n"
            "  $env:TEST_PASSWORD='<password>'\n"
            "  $env:NEXT_PUBLIC_FIREBASE_API_KEY='AIzaSyBYXZF1Py0vAgLwwChOOmxNsuY5kuMrng8'\n"
            "  $env:FIVVLE_TEST_TOKEN = (uv run python scripts/_get_token.py)",
            file=sys.stderr,
        )
        sys.exit(1)


def print_reader_phase_summary(exp_id: str, terminal_body: dict) -> None:
    """Summarize Reader-related polling fields.

    Structured ReaderOutput is not persisted on Experiment rows — see printed note below.
    """
    status = terminal_body.get("status")
    phases = terminal_body.get("phases_completed") or []
    phase_strs = [str(p) for p in phases]
    reading_seen = any(
        p.endswith("RESEARCH_READING") or p == "RESEARCH_READING" for p in phase_strs
    )

    print("\n--- B3 Reader smoke summary ---", flush=True)
    print(f"experiment_id={exp_id}", flush=True)
    print(f"completed_at_utc={datetime.now(UTC).isoformat()}", flush=True)
    print(f"terminal_status={status}", flush=True)
    print(f"phases_completed_count={len(phases)}", flush=True)
    print(f"phases_completed_json={json.dumps(phase_strs)}", flush=True)
    print(f"research_reading_in_phases_completed={reading_seen}", flush=True)

    print(
        "Per-question Reader fields (question_id, extracted_evidence_count, "
        "has_evidence_gap) are not returned by /research-status; structured "
        "ReaderOutput exists only in-process for the Synthesizer. Inspect "
        "application logs for 'reader question complete' events.",
        flush=True,
    )
    print(
        "URL / quote hallucination rollups are not persisted on the experiment; "
        "for systemic signals search logs for 'reader url hallucination detected' "
        "and 'reader quote hallucination rate exceeded'.",
        flush=True,
    )


# ---------------------------------------------------------------------------
# Steps
# ---------------------------------------------------------------------------


def step_sync_user(client: httpx.Client) -> None:
    log("syncing user...")
    resp = client.post("/users/sync", json={"name": "Smoke Test Founder"}, headers=HEADERS)
    resp.raise_for_status()
    log("user synced", user_id=resp.json().get("id"))


def step_create_experiment(client: httpx.Client) -> str:
    log("creating + refining experiment (1 LLM call)...")
    resp = client.post(
        "/experiments",
        json={"raw_idea": RAW_IDEA},
        headers=HEADERS,
        timeout=90.0,
    )
    resp.raise_for_status()
    body = resp.json()
    exp_id = body["id"]
    log("experiment created", experiment_id=exp_id, status=body["status"])
    assert body["status"] == "REFINED", f"Expected REFINED, got {body['status']}"
    return exp_id


def step_confirm(client: httpx.Client, exp_id: str) -> str:
    log("calling /confirm — dispatching research pipeline...")
    resp = client.post(f"/experiments/{exp_id}/confirm", headers=HEADERS)
    resp.raise_for_status()
    body = resp.json()
    assert resp.status_code == 202, f"Expected 202, got {resp.status_code}"
    log("202 accepted — pipeline dispatched", status=body["status"], status_url=body["status_url"])
    return body["status_url"]


def step_poll(client: httpx.Client, status_url: str) -> dict:
    """Poll until terminal status or ``MAX_POLLS`` exhausted."""
    log("polling /research-status...", interval_s=POLL_INTERVAL_SECONDS, max_polls=MAX_POLLS)
    for i in range(MAX_POLLS):
        resp = client.get(status_url, headers=HEADERS)
        resp.raise_for_status()
        body = resp.json()
        current_status = body["status"]
        label = body.get("phase_label") or ""
        phases = body.get("phases_completed", [])
        log(
            f"poll {i + 1}/{MAX_POLLS}",
            status=current_status,
            phase_label=label,
            phases_completed=len(phases),
        )
        if current_status == "RESEARCH_FAILED":
            log(
                "FAILED — pipeline reported failure",
                error_detail=body.get("error_detail"),
            )
            sys.exit(2)
        if current_status in _TERMINAL_STATUSES:
            log("SUCCESS — pipeline completed", phases_completed=phases)
            return body
        time.sleep(POLL_INTERVAL_SECONDS)

    log("TIMEOUT — pipeline did not reach a terminal status within the poll window")
    sys.exit(3)


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------


def main() -> None:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")

    check_token()

    # Optional: pass existing REFINED experiment UUID to skip refinement LLM call
    existing_id = sys.argv[1] if len(sys.argv) > 1 else None

    with httpx.Client(base_url=BASE_URL) as client:
        step_sync_user(client)

        if existing_id:
            log("using existing experiment (skipping create)", experiment_id=existing_id)
            exp_id = existing_id
        else:
            exp_id = step_create_experiment(client)

        status_url = step_confirm(client, exp_id)
        terminal_body = step_poll(client, status_url)
        print_reader_phase_summary(exp_id, terminal_body)


if __name__ == "__main__":
    main()
