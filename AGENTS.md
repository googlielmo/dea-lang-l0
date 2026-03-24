# AGENTS.md

Assistant guidance for the Dea/L0 repository.

Read `CLAUDE.md` first and treat it as the primary source of truth for project scope, commands, architecture, testing,
documentation, and constraints.

Important rules surfaced here so they are not missed:

- Follow the repo-local workflows and commands from `CLAUDE.md`; do not invent alternate setup/build/test flows.
- Do not revert unrelated user changes.
- Do not amend commits unless explicitly asked.
- Follow the git conventions in `CLAUDE.md`, including sentence-case commit summaries ending with a period and no
  `Co-Authored-By` lines.
- If changing documented behavior or ownership/stdlib/CLI/runtime behavior, update the corresponding docs in the same
  change.
- Pre-commit hooks may rewrite Markdown; if they do, stage the rewritten files and commit again.
