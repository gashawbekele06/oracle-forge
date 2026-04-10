# Oracle Forge — LLM Knowledge Base

Built using the Karpathy method: **minimum content, maximum precision, verified by injection test**.

## Structure

```
kb/
├── architecture/   — Claude Code + OpenAI agent architecture patterns
├── domain/         — DAB schema notes, join keys, terminology, unstructured fields
├── evaluation/     — DAB scoring, submission format, failure categories
└── corrections/    — Running log of agent failures → correct approaches
```

## Karpathy Discipline

Every document in this KB must pass this test before merging:

1. Take the document text.
2. Start a **fresh** LLM session with **only** that document as context (no other KB).
3. Ask a question the document should answer.
4. If the LLM answers correctly → document passes.
5. If the LLM gives a wrong or incomplete answer → revise or remove the document.

Test questions are recorded in each directory's `CHANGELOG.md`.

## Layer Injection Order

The `context_manager.py` injects layers in this order:
1. `architecture/` — loaded into AGENT.md context file (read by agent at startup)
2. `domain/` — injected after db_description in the system prompt (Layer 2)
3. `corrections/` — injected last, as the most specific and authoritative override (Layer 3)

## KB Maintenance Rules

- **Maximum 400 words per document** (Karpathy method: precision over volume).
- **Remove before adding**: before adding a new document, check if existing documents should be updated instead.
- **Version in CHANGELOG.md**: every change gets an entry with the date and a one-line summary.
- **Injection test before merge**: do not merge a document that hasn't passed the injection test.
- **Remove stale entries**: if a DB schema changes, update the relevant document immediately.
