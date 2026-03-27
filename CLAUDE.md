# CLAUDE.md

Guidance for Claude Code and AI agents working in this monorepo.

## Repository Structure

This is a monorepo for the Dea language family. Each language level is a self-contained subtree.

| Directory | Description                                           |
| --------- | ----------------------------------------------------- |
| `l0/`     | L0 language, compiler, stdlib, docs, and tests        |
| `tools/`  | Shared vendor dependencies and monorepo-level tooling |

## Per-Level Guidance

For L0-specific guidance, read `l0/CLAUDE.md`.

For human-facing monorepo structure and root workflow guidance, read `MONOREPO.md`.

## Root Makefile

The monorepo root `Makefile` is intentionally minimal. Use it only for monorepo maintenance:

- `make help`
- `make venv`
- `make clean`

Do not treat the root `Makefile` as a dispatcher for level-local build, test, or docs targets. For those, enter the
level directory first.
