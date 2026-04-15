# Signal Corps — External Engagement Log

Running log of all external posts, threads, and community interactions.
Updated daily. Required deliverable for submission.

---

## Week 8

### Day 1 — Resource Audit (April 10, 2026)
- [ ] Apply for Cloudflare Workers free tier: https://workers.cloudflare.com
- [ ] Identify 5 X accounts posting about data agents, Claude Code, or DAB
- [ ] Subscribe to DataAgentBench GitHub repo: https://github.com/ucbepic/DataAgentBench
- [ ] Note active subreddits: r/MachineLearning, r/LocalLLaMA
- [ ] Note Discord servers: Hugging Face, any DAB community

**Accounts identified posting about DAB/data agents**:
1. @ucbepic — Berkeley EPIC Data Lab (DAB paper authors)
2. @hasura — PromptQL team (DAB co-contributor)
3. @karpathy — Andrej Karpathy (LLM KB methodology)
4. @simonw — Simon Willison (AI tools practitioner)
5. @_jasonwei — AI research community

**Resources acquired**:
- Cloudflare Workers free tier: [ ] Applied / [ ] Approved
- API credits: [ ] Status pending

---

### Day 2 — First X Thread
**Topic**: Comment on the Claude Code architecture leak — three-layer memory system
**Observation shared**: The Claude Code MEMORY.md architecture maps directly to what production data agents need: index (fast routing) → topic files (domain knowledge) → session transcripts (corrections log). Oracle Forge implements this exact pattern for DAB.

**Post link**: [POST TO X — use this draft: "The Claude Code source leak shows why most data agents fail in production: they have context, not memory. Memory has three layers: index (what topics exist), topic files (what each topic means), session transcripts (what the user corrected). We built this for @ucbepic DataAgentBench. Thread 🧵"]
**Notable response**: [TO BE FILLED after posting]

---

### Day 3 — Internal Slack Daily + Community Entry
**Slack post**:
```
📊 Oracle Forge Daily — April 10, 2026

✅ Shipped: Three-layer context manager + full Docker stack running
🔧 Stuck: PATENTS dataset requires 5.42GB download not bundled with DAB
📈 Score: 49/54 pass@1 (91%) — PATENTS blocking final 5
➡️ Next: Download PATENTS DB, re-run benchmark, target 54/54

External post: X thread on Claude Code memory architecture (drafting)
```
**Reddit comment**: [POST TO r/MachineLearning — comment on any DataAgentBench or data agent post: "We're running Oracle Forge against DAB right now. The hardest part isn't SQL generation — it's join key format mismatches across DB types. PostgreSQL stores customer_id as integer 1001, DuckDB as 'CUST-0001001'. The agent has to detect and resolve this without being told. Our join_key_resolver utility handles 4 known formats automatically."]
**Link saved**: [TO BE FILLED after posting]

---

### Day 4 — Second X Thread
**Topic**: Engineering post on multi-database join key resolution
**Draft**: "The #1 reason AI data agents fail on real enterprise data: join key format mismatches. Same customer. Three databases. Three different ID formats: int 1001 | 'CUST-0001001' | 'C1001'. Our agent auto-detects the format and normalises before joining. Open-source: github.com/gashawbekele06/oracle-forge @ucbepic #DataAgentBench"
**Post link**: [TO BE FILLED after posting]
**Notable response**: [TO BE FILLED]

---

### Day 5 — Weekly Engagement Summary
**Posts sent this week**: 2 X threads drafted (post before April 14 deadline)
**Resources obtained**: Docker infrastructure running locally (no paid compute needed for benchmark)
**Community intelligence that changed technical approach**: DAB paper documents that ill-formatted join keys are a deliberate hard requirement — not a bug. This confirmed our join_key_resolver utility design was on the right track.

---

## Week 9

### Day 1 — Article Draft
**Topic**: One specific thing learned, one failure understood, one architectural decision made
**Draft location**: `signal/article_draft.md`

Example topics:
- "What DAB taught me about enterprise data reality"
- "The self-correcting execution loop: how we taught an agent to debug its own queries"
- "Why join key mismatches are the hardest problem in production data agents"

---

### Day 2 — Benchmark X Thread
**Topic**: Team's benchmark submission process — setup, first scores, what the evaluation harness measures
**Post link**: [TO BE FILLED]
**DAB repo tagged**: [ ] Yes / [ ] No

---

### Day 3 — Article Published
**Platform**: [ ] LinkedIn / [ ] Medium
**Article link**: [TO BE FILLED]
**X thread summarising key point**: [TO BE FILLED]

---

### Day 4 — Final Community Thread
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
