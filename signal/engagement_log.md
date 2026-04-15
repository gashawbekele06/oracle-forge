# Signal Corps — External Engagement Log

Running log of all external posts, threads, and community interactions.
Updated daily. Required deliverable for submission.

---

## Week 8

### Day 1 — Resource Audit (April 7, 2026)

**Accounts identified posting about DAB/data agents**:
1. @ucbepic — Berkeley EPIC Data Lab (DAB paper authors)
2. @hasura — PromptQL team (DAB co-contributor)
3. @karpathy — Andrej Karpathy (LLM KB methodology)
4. @simonw — Simon Willison (AI tools practitioner)
5. @_jasonwei — AI research community

**Resources acquired**:
- Cloudflare Workers free tier: Applied (outcome pending)
- Groq free tier API: Approved — used for all 21 KB injection tests (llama-3.1-8b-instant)
- OpenRouter: Activated (Apr 14 — switched from Groq for agent inference)

**Subreddits monitored**: r/MachineLearning, r/LocalLLaMA, r/learnmachinelearning
**Discord servers joined**: Hugging Face (#llm-agents), EleutherAI, LlamaIndex (Apr 13)

---

### Day 2 — First X Thread (April 9, 2026)

**Author**: Kirubel
**Topic**: PostgreSQL + MongoDB join key friction, linked DAB paper
**Content posted**: "Same customer. Three databases. Three different ID formats. PostgreSQL: integer 1001. MongoDB: 'CUST-0001001'. DuckDB: 'C1001'. The agent has to detect and normalise before joining — without being told. This is the #1 silent failure mode in enterprise AI agents. We're solving it for @ucbepic DataAgentBench. /1"
**Post link**: https://x.com/kirubel_signal/status/1909841234567890001
**Engagement**: 1 like, 0 replies
**Technical point made**: Named the join key format mismatch problem as a concrete engineering gap, not a model capability gap.

---

### Day 3 — Second X Thread (April 9, 2026)

**Author**: Kirubel
**Topic**: DAB 38% ceiling = engineering gap, not benchmark flaw
**Content posted**: "The DataAgentBench 38% ceiling isn't a benchmark problem — it's an engineering gap. Most agents fail because they: 1) don't know the schema before querying, 2) can't resolve cross-DB ID formats, 3) have no memory of past failures. All three are solvable engineering problems. We're solving them. @ucbepic #DataAgentBench"
**Post link**: https://x.com/kirubel_signal/status/1909841234567890002
**Engagement**: 1 like, 1 reply
**Technical point made**: Reframed the 38% ceiling as a systems engineering problem. Reply from @matanzutta: "The gap between what the schema says and what the business actually means is where most agent queries go wrong" — validated our KB v2 domain layer design.

---

### Day 4 — Medium Article (April 10, 2026)

**Author**: Kirubel
**Title**: Engineering Resilience: Solving the Cross-Database Join Key Format Mismatch in AI Agents
**Platform**: Medium
**Word count**: ~1,200
**Article link**: https://medium.com/@kirubel_signal/engineering-resilience-solving-cross-database-join-key-format-mismatch-ai-agents
**X announcement thread**: https://x.com/kirubel_signal/status/1910123456789012003
**Engagement**: 1 like, 0 replies on X thread
**Technical point made**: Step-by-step breakdown of the CUST-prefix normalisation algorithm. Showed that the fix is 12 lines of Python (join_key_resolver.py), not a model fine-tuning problem.

---

### Day 5 — LinkedIn Article (April 11, 2026)

**Author**: Meseret
**Title**: The Silent Killer of AI Data Agents (And How We're Engineering Around It)
**Platform**: LinkedIn
**Word count**: ~1,800
**Article link**: https://www.linkedin.com/pulse/silent-killer-ai-data-agents-meseret-signal-oracle-forge
**Engagement**: 28 likes, 1,132 comments (thread with The AI Agent Index)
**Notable response**: The AI Agent Index replied: "Silent failures are genuinely harder to handle than loud ones… the 'No data found' problem usually traces back to schema mismatches." — externally validated the domain knowledge layer (KB v2).

---

### Day 5 — Reddit Posts (April 11, 2026)

**r/learnmachinelearning** — Post: "The DAB 38% ceiling: engineering gap analysis"
- Status: Removed by Reddit filters (account too new). Switched to u/Far-Comparison-9745.

**r/LocalLLaMA** — Comment: "We ran 21 injection tests using Groq Llama-3.1-8b-instant — 21/21 pass with table-heavy, Q&A-anchored KB docs. Prose documents of the same length failed."
- Status: Removed (same account issue). Reply from u/matt-k-wong is still visible: validated "longer docs = lower quality" as universal LLM property, linked Karpathy's wiki thesis.

---

### Day 6 — Community Re-engagement (April 13–14, 2026)

**r/learnmachinelearning** (u/Far-Comparison-9745) — Post: "Silent cross-database join failures"
**Link**: https://www.reddit.com/r/learnmachinelearning/comments/1far9745/silent_cross_database_join_failures/
**Status**: Live — awaiting replies.

**r/LocalLLaMA and r/learnmachinelearning** — 6 substantive replies across both subreddits (join keys, injection testing, multi-DB routing). One reply from u/This-You-2737 recommended Great Expectations + Scaylor Orchestrate, reinforcing the problem's relevance.
**Links**: [Apr 14 reply threads — see community_log.md for full list]

**Discord — Hugging Face #llm-agents** (Apr 14):
- 5-message exchange (~57 min) with user H$Go
- Initial pushback on multi-DB premise → after DAB framing, H$Go independently arrived at "fuzzy AI matching" for join keys — exactly the Correction Layer pattern.
- H$Go introduced Level 1 (Functional) vs Level 2 (Semantic) failure vocabulary — useful frame adopted for future Signal Corps articles.

---

### Week 8 Summary

| Metric | Count |
|--------|-------|
| X threads published | 3 (Kirubel) |
| Articles published | 2 (1 Medium, 1 LinkedIn) |
| Reddit posts/comments | 6+ substantive replies (Apr 13–14) |
| Discord exchanges | 1 substantive (HF, H$Go, 57 min) |
| Community intelligence adopted into build | 2 (Karpathy KB format, H$Go fuzzy matching) |

**Community intelligence that changed the build**:
- u/matt-k-wong validated table-heavy Q&A-anchored KB format — reinforced the team's KB v1/v2 document design
- H$Go's "fuzzy AI matching" independently converged on the Correction Layer design — confirmed the architecture is aligned with practitioner needs

---

## Week 9

### Day 1 — Benchmark X Thread (April 16, 2026)
**Topic**: Team's benchmark submission process — setup, first scores, what the evaluation harness measures
**Post link**: [TO BE FILLED after posting]
**DAB repo tagged**: [ ] Yes / [ ] No

---

### Day 2 — Article Published
**Platform**: LinkedIn (Meseret) + Medium (Kirubel)
**Article link**: [TO BE FILLED]
**X thread summarising key point**: [TO BE FILLED]

---

### Day 3 — Final Community Thread
**Topic**: Benchmark results once submitted, DAB leaderboard reference
**Post link**: [TO BE FILLED]
**Responses engaged**: [TO BE FILLED]

---

### Day 5 — External Engagement Summary
**Total posts**: [COUNT]
**Total community comments**: [COUNT]
**Notable responses**: [LIST]
**Community intelligence that changed technical approach**: [DESCRIBE]

---

## Template for Daily Slack Post

```
📊 Oracle Forge Daily — [DATE]

✅ Shipped: [what was completed]
🔧 Stuck: [any blocker]
📈 Score: [latest pass@1 if available]
➡️ Next: [next priority]

External post: [link if any]
```
