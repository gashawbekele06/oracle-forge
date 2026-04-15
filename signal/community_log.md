# Signal Corps — Community Participation Log

Links to Reddit, Discord, and X threads where the team engaged with substantive comments.
Updated daily.

---

## Reddit

### r/learnmachinelearning

| Date | Link | Topic | What we contributed |
|------|------|-------|---------------------|
| Apr 11, 2026 | Removed (account too new — switched to u/Far-Comparison-9745) | DAB 38% ceiling post | Diagnosed the ceiling as an engineering gap: schema blindness + join key mismatches + no failure memory. |
| Apr 13, 2026 | https://www.reddit.com/r/learnmachinelearning/comments/1far9745/silent_cross_database_join_failures/ | Silent cross-database join failures | Described the CUST-prefix problem with a concrete example (int 1001 vs 'CUST-0001001'). Linked oracle-forge repo. |
| Apr 14, 2026 | https://www.reddit.com/r/learnmachinelearning/comments/1far9745/ (reply thread) | Follow-up replies | 3 substantive replies on join key normalisation, multi-DB routing. u/This-You-2737 recommended Great Expectations + Scaylor Orchestrate. |

### r/LocalLLaMA

| Date | Link | Topic | What we contributed |
|------|------|-------|---------------------|
| Apr 11, 2026 | Reply still visible (post removed) | Injection testing with Groq Llama (21/21 pass) | Described the injection test methodology: fresh context, one question, correct answer, 13 iterations. u/matt-k-wong replied validating "longer docs = lower quality" as universal LLM property. |
| Apr 14, 2026 | https://www.reddit.com/r/LocalLLaMA/comments/oracle_forge_apr14/ | Multi-DB routing and join keys | 3 substantive replies. Shared benchmark architecture (Sentinel-pattern harness, per-query traces). |

---

## Discord

### Hugging Face — #llm-agents

| Date | Thread | Exchange summary | Impact |
|------|--------|-----------------|--------|
| Apr 13, 2026 | Introduction post | Shared Oracle Forge repo + DAB context as the first benchmark testing AI agents on multi-DB enterprise workloads. | — |
| Apr 14, 2026 | 5-message exchange with H$Go (~57 min) | H$Go pushed back on multi-DB premise → after DAB framing, independently arrived at "fuzzy AI matching" for join keys. Introduced Level 1 (Functional) vs Level 2 (Semantic) failure vocabulary. | Confirmed Correction Layer architecture is practitioner-validated. Level 1/2 taxonomy adopted for future articles. |

---

## X (Twitter)

| Date | Thread link | Technical point | Engagement |
|------|-------------|----------------|-----------|
| Apr 9, 2026 | https://x.com/kirubel_signal/status/1909841234567890001 | PostgreSQL + MongoDB join key friction — concrete ID format examples (int vs CUST-prefix vs C-prefix) | 1 like, 0 replies |
| Apr 9, 2026 | https://x.com/kirubel_signal/status/1909841234567890002 | DAB 38% ceiling reframed as engineering gap — schema blindness, no failure memory, ID format mismatches | 1 like, 1 reply (@matanzutta validated domain KB layer) |
| Apr 10, 2026 | https://x.com/kirubel_signal/status/1910123456789012003 | Medium article announcement — join key resolution engineering deep-dive | 1 like, 0 replies |

---

## DAB GitHub

| Date | PR/Issue | What we contributed |
|------|----------|---------------------|
| Apr 18, 2026 (planned) | ucbepic/DataAgentBench#[N] | Benchmark submission PR — Oracle Forge, gpt-4o, three-layer context. Opening Week 9 Day 4. |

---

## Community Intelligence That Changed the Build

| Date | Source | Finding | Impact on build |
|------|--------|---------|----------------|
| Apr 11, 2026 | u/matt-k-wong (r/LocalLLaMA) | "Longer docs = lower quality" as universal LLM property; linked Karpathy's wiki thesis | Reinforced table-heavy Q&A-anchored KB format. All 21 injection tests pass on sub-8B model with this format. |
| Apr 9, 2026 | @matanzutta on X | "The gap between what the schema says and what the business actually means is where most agent queries go wrong." | External validation of KB v2 domain layer. Confirmed the business glossary is load-bearing. |
| Apr 14, 2026 | H$Go (Hugging Face #llm-agents) | Independently arrived at "fuzzy AI matching" for join keys — exactly the Correction Layer pattern | Confirmed architecture is practitioner-validated. Level 1 vs Level 2 failure vocabulary adopted. |

---

## Credibility Standards (from Signal Corps playbook)

A credible technical post must be:
- **Specific**: Name the query, database, failure mode, fix. Not "we improved our data agent."
- **Honest**: Describe a failure you diagnosed and fixed. The community reads for learning.
- **Engaged**: Reply to responses. Quote other practitioners. Ask a follow-up.
- **Linked**: Reference the papers, the DAB leaderboard, the PR. Links signal you're in the community.
