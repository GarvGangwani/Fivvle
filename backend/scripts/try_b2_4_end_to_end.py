#!/usr/bin/env python
"""B2.4 end-to-end smoke test — runs ONLY against localhost with in-process dispatcher.

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
MAX_POLLS = 45  # 45 × 8s = 6 minutes timeout

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


def step_poll(client: httpx.Client, status_url: str) -> None:
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
        if current_status == "RESEARCH_READY":
            log("SUCCESS — pipeline completed", phases_completed=phases)
            return
        if current_status == "RESEARCH_FAILED":
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
        step_poll(client, status_url)


if __name__ == "__main__":
    main()
