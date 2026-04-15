# Tool Design Philosophy — Claude Code Architecture

**Injection test**: Ask "How many tools does Claude Code expose and what is the scoping principle?" → should answer "40+ tools with tight domain boundaries; each tool does one thing with minimal side effects."

## Core Principle: Tight Domain Boundaries

Claude Code exposes 40+ tools, each scoped to a **single, specific action**. No tool does two things. This is the opposite of a "universal tool" design.

**Why**: When a tool can do multiple things, the LLM must decide which behaviour to invoke. When it does one thing, the LLM decides only whether to invoke it.

## Tool Categories from the Source Leak

| Category | Examples | Scope |
|---|---|---|
| File I/O | `Read`, `Write`, `Edit` | One file, one operation |
| Search | `Grep`, `Glob` | One search type per tool |
| Execution | `Bash` | Single shell command |
| Agent | `Agent`, `SendMessage` | Spawn or communicate with sub-agent |
| Memory | `TodoWrite`, `ScheduleWakeup` | Structured state mutation |

## Tool Scoping Rules (from source)

1. **No side effects beyond stated purpose** — `Read` never writes; `Write` never reads.
2. **Fail loudly** — if parameters are wrong, error immediately. Never silently succeed on wrong input.
3. **Idempotent where possible** — running `Write` twice with same content → same result.
4. **One abstraction level per tool** — `Bash` is low-level; `Agent` is high-level. They don't overlap.

## Application to Oracle Forge

DataAgentBench tools follow the same principle:

| DAB Tool | Single responsibility |
|---|---|
| `query_db` | Execute one query against one database |
| `list_db` | List tables/collections in one database |
| `execute_python` | Run one Python code block in sandbox |
| `return_answer` | Terminate with final answer (no side effects) |

**Key implication**: The agent must call `query_db` once per database. Cross-database joins happen in `execute_python` via pandas — not by passing multi-database SQL to a single tool.
