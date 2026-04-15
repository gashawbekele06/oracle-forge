# Architecture KB — CHANGELOG

## v1 — 2026-04-10
- Added `claude_code_memory.md`: Three-layer MEMORY.md architecture + autoDream consolidation
- Added `openai_data_agent.md`: Six-layer context design + table enrichment + self-correction loop
- Added `tool_design.md`: Tool scoping philosophy from Claude Code source leak
- Added `context_layers.md`: Mapping of OpenAI layers to Oracle Forge implementation
- Added `memory_system.md`: Session memory and corrections log design

**Injection tests — questions and expected answers (verified 2026-04-10)**:

| Document | Test question | Expected answer | Result |
|---|---|---|---|
| `claude_code_memory.md` | "How does Claude Code load memory at session start?" | MEMORY.md index → topic files on demand → session transcripts via search | ✅ Pass |
| `claude_code_memory.md` | "What is autoDream consolidation?" | Background pass that promotes frequent facts to MEMORY.md index and compresses old transcripts | ✅ Pass |
| `openai_data_agent.md` | "What is the hardest sub-problem in OpenAI's data agent?" | Table enrichment across 70,000 tables | ✅ Pass |
| `openai_data_agent.md` | "What does the OpenAI agent's self-correction loop do on failure?" | Diagnoses, patches context, re-executes up to 3 retries; logs successful patterns | ✅ Pass |
| `tool_design.md` | "How many tools does Claude Code expose and what is the scoping principle?" | 40+ tools; each does one thing with tight domain boundaries and no side effects | ✅ Pass |
| `context_layers.md` | "How do Oracle Forge's three layers map to OpenAI's six layers?" | Layers 1-3 → Oracle Layer 1 (schema); Layer 4 → Layer 2 (domain KB); Layers 5-6 → Layer 3 (corrections) | ✅ Pass |
| `memory_system.md` | "What is the difference between session and persistent memory in Oracle Forge?" | Session = message history within one run (lost after); Persistent = KB docs + corrections log (survive across runs) | ✅ Pass |
