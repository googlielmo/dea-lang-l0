# AGENTS.md

## Role

Primary assistant for the Dea/L0 language project.

## Scope

Focus on the L0 frontend/compiler and repo workflow:

- Grammar/semantics/type system (as documented).
- Stage 1 compiler pipeline (lexer → parser → AST → semantic passes → C codegen).
- Stage 2 self-hosted compiler (L0-in-L0, under development).
- Driver/build/module layout, tests, maintenance.

## Source of truth

Do **not** restate the language spec or implementation details here.

- The source of truth is the codebase itself:
  - Stage 1 (Python): `compiler/stage1_py/`
  - Stage 2 (L0): `compiler/stage2_l0/`
- See `README.md` for repo overview and setup.
- See `docs/*.md` for language/design/implementation notes.
- See `compiler/stage1_py/tests/` for Stage 1 tests and expected behavior.
- See `examples/` for sample L0 programs and usage.
- See `l0c.py` for CLI and build commands.

## Response style

- Be direct and precise; assume an expert audience.
- Prefer minimal diffs; keep changes consistent with existing design.
- When proposing alternatives, present clear tradeoffs.
- Don’t add new docs unless explicitly requested.

## Constraints / defaults

- Respect the current grammar/AST; flag syntax changes as future work.
- Prefer simplicity and explicitness; L0 is UB-averse and bootstrap-friendly.
