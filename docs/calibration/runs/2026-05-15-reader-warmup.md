\# Reader Warm-Up Run — 2026-05-15



\*\*Idea:\*\* AI assistant for sales reps drafting follow-up emails from CRM + LinkedIn activity

\*\*Experiment ID:\*\* 50dbefd6-1dbd-49db-b3c2-dce48bbe7016

\*\*Anthropic prompt version:\*\* reader\_v1

\*\*Status:\*\* RESEARCH\_READY



\## Cost breakdown



| Phase | Calls | Cost | Notes |

|---|---|---|---|

| Refinement | 1 | $0.018 | |

| Planner | 1 | $0.036 | |

| Reader | 7 | $0.454 | 56% of LLM cost |

| Synthesizer | 1 | $0.304 | Still consuming raw Tavily (Synthesizer refactor pending) |

| Tavily | 21 | $0.336 | |

| \*\*TOTAL\*\* | | \*\*$1.15\*\* | |



\## Per-Reader-call detail



| Call | Cost | In tokens | Out tokens | Latency |

|---|---|---|---|---|

| 1 | $0.044 | 9,265 | 1,075 | 19s |

| 2 | $0.044 | 7,997 | 1,331 | 26s |

| 3 | $0.051 | 9,538 | 1,483 | 27s |

| 4 | $0.046 | 7,847 | 1,519 | 28s |

| 5 | $0.093 | 20,625 | 2,054 | 68s |

| 6 | $0.052 | 8,990 | 1,644 | 87s |

| 7 | $0.125 | 20,997 | 4,112 | 115s |



\## Observations



\- Pipeline works end-to-end with Reader wired in.

\- Synthesizer output coherent. Real competitors named (Lavender, Regie.ai, Amplemarket). Citations point to real domains.

\- Reader latency: concurrent execution caps total Reader wall-clock at the slowest call (\~115s = \~2 min).

\- Synthesizer latency: 226s (3.8 min) — still the bottleneck. Confirms Synthesizer refactor is high-leverage post-calibration.

\- Two Reader calls (#5, #7) had \~2× input tokens and \~3× cost of baseline. Pattern to watch in calibration: input variance correlates with cost.

\- Reader hallucination counters not captured this run (logs stdout-only, not persisted). Future runs should tee uvicorn output to a file.



\## Recommendation



Ready for full 5-idea calibration session. Top up Anthropic to \~$30 before starting.



\## Anomalies



None blocking. Note for next run: tee uvicorn output to file so Reader structured logs persist for calibration analysis.





\## 2026-05-15 mini-calibration attempt (aborted)



Attempted 3-idea mini-calibration with deliberately hard ideas (vet HIPAA scribe, software architect whiteboard, parent craft subscription) to stress-test the pipeline.



\*\*Result:\*\* First idea (vet scribe) failed twice at Synthesizer phase with Anthropic Tier 1 rate limit (30,000 input tokens/min). Synthesizer's \~47k token input cannot fit through the cap.



\*\*Implication:\*\* Synthesizer refactor is no longer a cost optimization — it is a hard blocker for any consistent pipeline operation on Tier 1. Reader output ingestion (drops Synthesizer input from \~47k → \~20-30k tokens) is the unblock.



Calibration deferred until Synthesizer refactor lands. Will run full 5-idea calibration against the refactored pipeline.



Note: rate limit also blocks Tier 1 from running multi-idea sessions in close succession even if individual calls fit, since per-minute caps reset slowly.

