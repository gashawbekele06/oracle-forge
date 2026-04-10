# Claude Code Three-Layer Memory Architecture

**Injection test**: Ask "How does Claude Code load memory at session start?" → should answer with MEMORY.md index + topic files + session transcripts.

## How It Works

Claude Code uses a **three-layer persistent memory system**:

### Layer 1: MEMORY.md Index
- A root index file listing all memory topics as one-line pointers.
- Always loaded into context; truncated after 200 lines.
- Each entry: `- [Title](file.md) — one-line hook`
- Purpose: fast routing — tells the agent what topics exist without loading detail.

### Layer 2: Topic Files (on-demand)
- Separate markdown files per topic (user profile, project state, feedback, references).
- Loaded only when a topic is relevant to the current task.
- Types: `user/`, `feedback/`, `project/`, `reference/`
- Each file has frontmatter: `name`, `description`, `type`.

### Layer 3: Session Transcripts (searchable)
- Full conversation history stored and searchable by semantic query.
- Not loaded by default — retrieved on demand via search.
- Used for: "what did the user say about X last week?"

## autoDream Consolidation

After long sessions, Claude Code runs a background consolidation pass:
- Promotes frequently-accessed topic-file facts into MEMORY.md index hints.
- Compresses verbose session transcripts into summary bullets.
- Removes stale or contradicted entries.

This prevents unbounded KB growth and ensures the index stays relevant.

## Application to Oracle Forge

| Claude Code Layer | Oracle Forge Equivalent |
|---|---|
| MEMORY.md index | `kb/` directory listing, AGENT.md |
| Topic files | `kb/architecture/`, `kb/domain/`, `kb/evaluation/` |
| Session transcripts | `kb/corrections/corrections_log.md` |
| autoDream | Periodic KB review + removal of outdated entries |
