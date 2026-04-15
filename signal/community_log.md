# Signal Corps — Community Participation Log

Links to Reddit, Discord, and X threads where the team engaged with substantive comments.
Updated daily.

---

## Reddit

### r/MachineLearning
| Date | Link | Topic | What we contributed |
|------|------|-------|---------------------|
| Apr 10, 2026 | [POST LINK] | DataAgentBench / enterprise data agents | Described the join key mismatch problem: same customer, three DBs, three ID formats. Shared our open-source join_key_resolver utility. **[POST THIS COMMENT before April 14 deadline]** |

### r/LocalLLaMA
| Date | Link | Topic | What we contributed |
|------|------|-------|---------------------|
| Apr 12, 2026 | [POST LINK] | LLM tool use / multi-step agents | Explained how DAB tests agents on real enterprise workloads — not clean single-table SQL. Shared benchmark score (54/54 with gpt-4o, corrections log architecture). **[POST BEFORE DEADLINE]** |

---

## Discord

### Hugging Face
| Date | Channel | Thread | What we contributed |
|------|---------|--------|---------------------|
| Apr 11, 2026 | #llm-agents | Data agent tools | Shared Oracle Forge repo link + note that DAB is the first benchmark testing AI agents on multi-DB enterprise workloads. Offered to answer questions about the DAB setup. **[POST BEFORE DEADLINE]** |

---

## X (Twitter)

| Date | Thread link | Context | What we said |
|------|-------------|---------|--------------|
| Apr 10, 2026 | [LINK after posting] | Claude Code memory architecture | Three-layer memory system observation + Oracle Forge implementation mapping |
| Apr 11, 2026 | [LINK after posting] | Multi-DB join key resolution | Technical thread on CUST- prefix mismatch and auto-resolver utility |

---

## DAB GitHub

| Date | PR/Issue | What we contributed |
|------|----------|---------------------|
| Apr 15, 2026 | ucbepic/DataAgentBench#[N] | Benchmark submission PR — Oracle Forge, 54/54 pass@1=1.0, gpt-4o, three-layer context |

---

## Credibility Standards (from Signal Corps playbook)

A credible technical post must be:
- **Specific**: Name the query, database, failure mode, fix. Not "we improved our data agent."
- **Honest**: Describe a failure you diagnosed and fixed. The community reads for learning.
- **Engaged**: Reply to responses. Quote other practitioners. Ask a follow-up.
- **Linked**: Reference the papers, the DAB leaderboard, the PR. Links signal you're in the community.
