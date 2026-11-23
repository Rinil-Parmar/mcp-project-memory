# Phase 0 — Manual Memory Validation

## Purpose

Determine whether a compact project-state file improves a fresh AI chat before automating it.

## Test setup

- Date:
- AI client and model:
- Tester:
- State file version/commit:

Run the same questions in two fresh chats:

1. Baseline: do not provide `PROJECT_STATE.md`.
2. Manual memory: instruct the assistant to read `PROJECT_STATE.md` first.

## Questions and results

| Question | Baseline result | With state file | Better? | Notes |
|---|---|---|---|---|
| What are the non-negotiable constraints? | | | | |
| What storage and transport were chosen, and why? | | | | |
| Which alternatives were rejected? | | | | |
| What should we work on next? | | | | |
| Why are records superseded instead of overwritten? | | | | |

## Friction observed

- What was tedious to maintain manually?
- What information was missing?
- What information was unnecessary?
- Did any stored statement appear more authoritative than it should?

## Decision

- [ ] Pass: structured automated memory is worth building.
- [ ] Revise: change the manual format and repeat.
- [ ] Stop: the improvement does not justify a separate tool.

Evidence and conclusion:
