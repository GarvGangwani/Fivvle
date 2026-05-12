# B1 Manual Verification — curl Playbook

Run this **after** you have:
1. Applied the Alembic migration (`uv run alembic upgrade head`)
2. Started the dev server (`uv run uvicorn app.main:app --reload`)

All commands assume `BASE=http://localhost:8000`.

---

## 0. Get a Firebase ID Token

The backend validates real Firebase ID tokens. Two options:

### Option A — Python snippet (requires a service account or the Firebase REST API)

```python
import httpx, os

# Uses Firebase Auth REST API — no service account needed.
# Requires EMAIL_ADDRESS and PASSWORD of a real test account in your Firebase project.
resp = httpx.post(
    f"https://identitytoolkit.googleapis.com/v1/accounts:signInWithPassword"
    f"?key={os.environ['NEXT_PUBLIC_FIREBASE_API_KEY']}",
    json={
        "email": os.environ["TEST_EMAIL"],
        "password": os.environ["TEST_PASSWORD"],
        "returnSecureToken": True,
    },
)
print(resp.json()["idToken"])
```

Export the token:

```bash
export TOKEN="<paste idToken here>"
```

### Option B — Firebase CLI

```bash
# Requires firebase-tools and a logged-in account.
export TOKEN=$(firebase auth:print-access-token)
```

---

## 1. Sync the test user (required before any experiment endpoint)

```bash
curl -s -X POST "$BASE/users/sync" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"name": "Test Founder"}' | jq .
```

Expected: `200 OK`, body contains `id`, `email`, `name`.

---

## 2. Create an experiment (POST /experiments)

```bash
curl -s -X POST "$BASE/experiments" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "raw_idea": "I want to build a Slack bot that answers HR policy questions instantly so operations managers no longer have to answer the same questions 20-30 times per week."
  }' | jq .
```

Expected: `201 Created`

Response shape:
```json
{
  "id": "<uuid>",
  "user_id": "<uuid>",
  "slug": null,
  "raw_idea": "...",
  "refined_idea": {
    "refined_one_liner": "...",
    "target_audience": "...",
    "value_proposition": "...",
    "risks": ["...", "...", "..."],
    "headline": "...",
    "subheadline": "...",
    "cta_text": "..."
  },
  "status": "REFINED",
  "refinement_count": 1,
  "created_at": "...",
  "updated_at": "..."
}
```

Export the experiment id:

```bash
export EXP_ID="<paste id from above>"
```

---

## 3. Regenerate with feedback (POST /experiments/{id}/refine)

```bash
curl -s -X POST "$BASE/experiments/$EXP_ID/refine" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"feedback": "Make the target audience more specific — which industries and company sizes?"}' \
  | jq .
```

Expected: `200 OK`, `"refinement_count": 2`, `"status": "REFINED"`.

---

## 4. Wrong experiment ID → 404

```bash
curl -s -X POST "$BASE/experiments/00000000-0000-0000-0000-000000000000/refine" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{}' | jq .
```

Expected: `404 Not Found`, `{"detail": "Experiment not found"}`.

---

## 5. Unauthenticated request → 401

```bash
curl -s -X POST "$BASE/experiments" \
  -H "Content-Type: application/json" \
  -d '{"raw_idea": "A tool for nurses."}' | jq .
```

Expected: `401 Unauthorized`, `{"detail": "Authentication required"}`.

---

## 6. Hit the regeneration cap (5 times → 409 on the 6th)

Run the refine command from step 3 three more times (without feedback is fine):

```bash
for i in 3 4 5; do
  echo "--- Regeneration $i ---"
  curl -s -X POST "$BASE/experiments/$EXP_ID/refine" \
    -H "Authorization: Bearer $TOKEN" \
    -H "Content-Type: application/json" \
    -d '{}' | jq '.refinement_count, .status'
done
```

Then the 6th attempt:

```bash
curl -s -X POST "$BASE/experiments/$EXP_ID/refine" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{}' | jq .
```

Expected: `409 Conflict`, `{"detail": "Regeneration limit reached for this experiment"}`.

---

## 7. Confirm LLMCall rows were written

Check cost tracking via the admin endpoint (requires an admin user — set `is_admin=true`
directly in the DB for your test user, or use the admin fixture if one exists):

```bash
curl -s "$BASE/admin/cost/experiment/$EXP_ID" \
  -H "Authorization: Bearer $TOKEN" | jq .
```

Expected: a list of `llm_calls` rows, each with `phase="refinement"`,
`prompt_tokens > 0`, `completion_tokens > 0`, `cost_usd > 0`.

You should see one row per refinement (initial + regenerations).
For 5 regenerations + 1 initial = **6 LLMCall rows**.

---

## Notes

- The `refined_idea` JSON stored in `experiments.refined_idea` (JSONB column) must
  match the `RefinedIdea` schema exactly (`refined_one_liner`, `target_audience`,
  `value_proposition`, `risks`, `headline`, `subheadline`, `cta_text`).
- `slug` is `null` at this stage. It is populated when the founder publishes the
  landing page (B3/FE5).
- If the LLM call fails during creation, the experiment row is **not saved** (the
  entire transaction is rolled back). The response is `502`; the client retries with
  a fresh `POST /experiments`.
