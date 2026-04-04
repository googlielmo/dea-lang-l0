# L1 Documentation Layout

This `l1/docs/` tree holds stable documentation for the Dea/L1 subtree.

At the current bootstrap stage, this tree is still intentionally narrow:

- L1 bootstrap/reference documents
- future L1 language/compiler specs once they exist

L1-local lifecycle artifacts live in the sibling `l1/work/` tree. Dea-wide stable docs live under the root `docs/` tree,
while Dea-wide lifecycle artifacts live under the root `work/` tree.

## Layout

- `reference/` for L1-local status/bootstrap references
- `specs/` for future L1-local specifications
- `implementation/` for future accepted implementation notes if needed

Use `l1/work/plans/` for L1-local plans. If L1 work is actually shared with L0 or the monorepo, prefer one shared
root-owned plan under `work/plans/` instead of opening an L1-only follow-up plan for a mechanical downstream port.
