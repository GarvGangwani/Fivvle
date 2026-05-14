#!/usr/bin/env python
"""B2.4 end-to-end smoke test — runs ONLY against localhost with in-process dispatcher.

Usage:
    # From the backend directory with the server running:
    uv run python scripts/try_b2_4_end_to_end.py

Prerequisites:
    - FastAPI server running locally: uv run uvicorn app.main:app --reload
    - DISPATCHER_MODE=in_process (default)
    - A valid Firebase custom token (see KILL_BEFORE note below)

KILL_BEFORE note (from B2.4 smoke test post-mortem):
    Kill the script (Ctrl-C) IMMEDIATELY after seeing "202 accepted" in the log,
    NOT after watching log lines stream. Planner LLM calls cost real money (~$0.001
    each). See docs/cost-ledger.md.

DO NOT run this against staging/production.
"""

from __future__ import annotations

import json
import sys
import time

import httpx

# ---------------------------------------------------------------------------
# Configuration — edit these before running
# ---------------------------------------------------------------------------

BASE_URL = "http://localhost:8000"
FIREBASE_ID_TOKEN = "REPLACE_ME"  # Paste a real ID token from browser localStorage
RAW_IDEA = (
    "A tool that helps solo founders validate their SaaS ideas before writing "
    "a single line of code. The founder describes their idea, and the tool runs "
    "automated research (market size, competition, pricing) and produces a "
    "go/no-go recommendation with citations."
)
POLL_INTERVAL_SECONDS = 5
MAX_POLLS = 36  # 36 × 5s = 3 minutes timeout

# ---------------------------------------------------------------------------
# Helper
# ---------------------------------------------------------------------------

HEADERS = {"Authorization": f"Bearer {FIREBASE_ID_TOKEN}"}


def log(msg: str, **fields: object) -> None:
    parts = " ".join(f"{k}={v!r}" for k, v in fields.items())
    print(f"[smoke] {msg} {parts}".strip(), flush=True)


def check_token() -> None:
    if FIREBASE_ID_TOKEN == "REPLACE_ME":
        print(
            "ERROR: Set FIREBASE_ID_TOKEN at the top of this script before running.",
            file=sys.stderr,
        )
        sys.exit(1)


# ---------------------------------------------------------------------------
# Steps
# ---------------------------------------------------------------------------


def step_sync_user(client: httpx.Client) -> None:
    log("syncing user...")
    resp = client.post("/users/sync", json={"name": "Smoke Test Founder"}, headers=HEADERS)
    resp.raise_for_status()
    log("user synced", user_id=resp.json().get("id"))


def step_create_experiment(client: httpx.Client) -> str:
    log("creating experiment (LLM call — watch your cost ledger)...")
    resp = client.post(
        "/experiments",
        json={"raw_idea": RAW_IDEA},
        headers=HEADERS,
        timeout=60.0,
    )
    resp.raise_for_status()
    body = resp.json()
    exp_id = body["id"]
    log("experiment created", experiment_id=exp_id, status=body["status"])
    assert body["status"] == "REFINED", f"Expected REFINED, got {body['status']}"
    return exp_id


def step_confirm(client: httpx.Client, exp_id: str) -> str:
    log("calling /confirm — KILL IMMEDIATELY AFTER THIS 202 if you want to save cost...")
    resp = client.post(f"/experiments/{exp_id}/confirm", headers=HEADERS)
    resp.raise_for_status()
    body = resp.json()
    assert resp.status_code == 202, f"Expected 202, got {resp.status_code}"
    log("202 accepted", status=body["status"], status_url=body["status_url"])
    return body["status_url"]


def step_poll(client: httpx.Client, status_url: str) -> None:
    log("polling /research-status...", interval_s=POLL_INTERVAL_SECONDS)
    for i in range(MAX_POLLS):
        resp = client.get(status_url, headers=HEADERS)
        resp.raise_for_status()
        body = resp.json()
        status = body["status"]
        label = body.get("phase_label") or ""
        phases = body.get("phases_completed", [])
        log(
            f"poll {i + 1}/{MAX_POLLS}",
            status=status,
            phase_label=label,
            phases_completed=len(phases),
        )
        if status == "RESEARCH_READY":
            log("SUCCESS — pipeline completed", phases_completed=phases)
            return
        if status == "RESEARCH_FAILED":
            log(
                "FAILED — pipeline reported failure",
                error_detail=body.get("error_detail"),
            )
            sys.exit(2)
        time.sleep(POLL_INTERVAL_SECONDS)

    log("TIMEOUT — pipeline did not complete within the poll window")
    sys.exit(3)


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------


def main() -> None:
    check_token()
    with httpx.Client(base_url=BASE_URL) as client:
        step_sync_user(client)
        exp_id = step_create_experiment(client)
        status_url = step_confirm(client, exp_id)
        step_poll(client, status_url)


if __name__ == "__main__":
    main()
