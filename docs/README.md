# Root Documentation Layout

This root `docs/` tree is for Dea-wide and monorepo-wide documentation.

Today it contains:

- Dea-wide plans that are not owned by one language level
- monorepo layout and shared automation work
- Dea-wide reference/status documents that describe the project as a whole
- future cross-level design and release-process documents

Existing level-local documentation remains in the owning subtree such as `l0/docs/`.

## Plans

Root plans live under `docs/plans/` and follow the same category split used by level-local docs:

- `features/`
- `bug-fixes/`
- `refactors/`
- `tools/`

Active plans live at the category root. Closed plans live under `<category>/closed/`.

## Reference

Root reference docs live under `docs/reference/` and describe the whole Dea project rather than one language level.

Examples:

- overall project status
- monorepo-wide release/status policy
- cross-level architecture notes once they exist

Language-specific references live in the owning subtree such as `l0/docs/reference/`.
