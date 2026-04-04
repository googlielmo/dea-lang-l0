# L1 Work Layout

This `l1/work/` tree holds lifecycle-bound documents for the Dea/L1 subtree.

Use `l1/docs/` for stable references and future accepted specs. Use `l1/work/` for plans and any future proposals.

## Layout

- `plans/` for L1-local execution plans and operational work tracking
- `proposals/` for future in-discussion L1 changes if that tree becomes necessary

Active plans live at the category root. Closed plans move into `<category>/closed/`.

Use `l1/work/plans/` only for work owned by the L1 subtree. If a fix or refactor spans `l0/` and `l1/`, prefer one
shared root plan under `work/plans/` with explicit targets rather than separate local follow-up plans.
