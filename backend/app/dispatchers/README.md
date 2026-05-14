# Research Dispatcher — Structlog Field Contract

> **Enforced by:** Convention and code review (per ADR 0009 "What we accept").
> All dispatcher implementations MUST emit these fields on every log event.
> Omitting a field from one implementation but not the other silently breaks
> log queries that work uniformly across dev and prod (Cloud Logging).

## Mandatory Fields

| Field | Type | Values | Notes |
|---|---|---|---|
| `dispatcher` | `str` | `"in_process"` \| `"http"` | Set from the implementation, not from config |
| `experiment_id` | `str` | UUID as string | Always `str(experiment_id)` — never raw UUID object |
| `phase` | `str` | `"dispatched"` \| `"completed"` \| `"failed"` | Set at each transition |

## Phase Semantics

| `phase` | When emitted | Level |
|---|---|---|
| `"dispatched"` | Immediately before `create_task` / before POST to Cloud Function | `info` |
| `"completed"` | Task done-callback confirms success | `info` |
| `"failed"` | Scheduling error OR task raised unexpected exception | `error` |

## Example Log Queries (Cloud Logging / structlog)

```
# All failed research dispatches in the last 24h
jsonPayload.phase="failed" AND jsonPayload.experiment_id!=null

# Compare dispatch latency across modes
jsonPayload.dispatcher="in_process" AND jsonPayload.phase="dispatched"
jsonPayload.dispatcher="http" AND jsonPayload.phase="dispatched"
```

## Adding a New Field

If you add a field to one implementation (e.g. `http_status_code` on
HttpDispatcher), you MUST add a counterpart to InProcessDispatcher (e.g.
`http_status_code=None` or a meaningful equivalent).  The goal is that
log queries written against dev logs work against prod logs without changes.

## B3 Note

When the HttpDispatcher is fully implemented in B3, it should add:
- `http_status_code: int` — response code from the Cloud Function
- `latency_ms: float` — wall-clock time of the HTTP POST

InProcessDispatcher should add these as `None` at the same phase checkpoints.
