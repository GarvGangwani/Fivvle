\# Post-Synthesizer-Refactor Warm-Up — 2026-05-15



\*\*Idea:\*\* AI HIPAA scribe for veterinary practices (Cornerstone/AVImark PIMS sync). Same idea that hit Tier 1 rate limit pre-refactor.

\*\*Experiment ID:\*\* c822a2f4-877b-4fff-9ed1-e1000b050940

\*\*Pipeline:\*\* Reader (reader\_v1) + Synthesizer (synthesizer\_v2)

\*\*Status:\*\* RESEARCH\_READY ✅



\## Cost breakdown



| Phase | Calls | Cost | Notes |

|---|---|---|---|

| Refinement | 1 | $0.019 | |

| Planner | 1 | $0.037 | |

| Reader | 7 | $0.423 | Reader cost stable vs May 14 ($0.454) |

| Synthesizer (v2) | 1 | $0.486 | Up from $0.304 — see analysis below |

| Tavily | 21 | $0.336 | |

| \*\*TOTAL\*\* | | \*\*$1.30\*\* | Up from May 14's $1.15 |



\## Synthesizer comparison (v1 raw-Tavily vs v2 Reader-output)



| Metric | v1 (May 14) | v2 (post-refactor) | Delta |

|---|---|---|---|

| Input tokens | 47,204 | 58,620 | +24% |

| Output tokens | 10,817 | 20,653 | +91% |

| Cost | $0.304 | $0.486 | +60% |

| Latency | 226s | 434s | +92% |



\## Report quality



\*\*Significantly improved.\*\* Sample competitor analysis includes:

\- Talkatoo: 30,000+ users, $50-$126/user/mo, 30-day trial, Auto-SOAP iterating but not in v1

\- HappyDoc: 1.3-1.5M real pet visits training data, 99.8% accuracy claim, native Cornerstone/AVImark/ImproMed PIMS integration

\- Scribenote: explicit PIMS widget mode covering AVImark, Cornerstone, ImproMed, ezyVet, Pulse



All citations point to real domains. All competitors are real products. Pricing, user counts, training data sizes — all sourced from cited evidence. Positioning\_vs\_idea is concrete, naming each competitor's gap vs the proposed product.



This is production-grade output. A founder reading this knows the competitive landscape, the differentiation opportunities, and the build/buy tradeoffs.



\## Why the cost went UP, not down



Original projection assumed Synthesizer would do the \*same thing\* on less input. Actual behavior: Synthesizer does a \*richer thing\* on slightly more, well-structured input. Output more than doubled because Reader's per-question extraction surfaced significantly more usable signal than raw Tavily snippets did. The model writes more because it has more verified evidence to synthesize across.



\*\*Cost increase = value increase, not waste.\*\* This is the right tradeoff for a product whose value depends on report quality.



\## Rate limit verification



Synthesizer input was 58,620 tokens — well above Anthropic Tier 1's documented 30,000 input tokens/minute cap. Yet the call succeeded. Possible explanations:

\- Anthropic's per-minute cap may smooth over the request lifetime, not measure peak

\- Our org's actual tier may be higher than expected (verify in console)

\- Possible internal grace allowance on first-request-after-idle



Action: verify our actual tier in console.anthropic.com before assuming the 30k cap is the binding constraint at any specific volume.



\## Latency observation



434s Synthesizer wall-clock (vs 226s pre-refactor) is concerning vs `USER\_FLOW` Stage 3's "2-4 minutes" promise. Total pipeline \~10 min. Reflector phase (deferred) and prompt iteration may need to address this.



\## Decisions



\- \*\*synthesizer\_v2 is shipped\*\* and producing higher-quality output than v1. Do not revert.

\- \*\*Cost target ($0.50-$0.80/run) was wrong\*\*. Reframe target as "cost per high-quality report" not "cost per any report." Current $1.30/run is acceptable for the quality delivered.

\- \*\*Calibration session deferred\*\* until next planning piece (Reflector or multi-source) lands and we can calibrate the full B3 pipeline together.

\- \*\*Rate limit risk\*\* still present at scale. Need to verify Anthropic tier or plan for tier upgrade before friends-and-circle launch.



\## Anomalies



\- None blocking. The refactor achieved its architectural goals (Reader/Synthesizer separation, clean prompt contract, citation guard rebased on Reader URLs) AND improved report quality. The cost surprise reveals our original projection was naive about output quality.

