# Dea Monorepo

This repository hosts the Dea language family as a monorepo.

## Root Workflow

The monorepo root owns a minimal maintenance `Makefile`:

```bash
make help   # show root-only monorepo targets
make venv   # create or sync the shared .venv
make clean  # clean each registered level plus root caches/artifacts
```

The root `Makefile` is not a dispatcher for level-specific targets. Build, test, docs, and compiler workflows should be
run inside the relevant level directory.

## Language Levels

| Directory | Description                                                   |
| --------- | ------------------------------------------------------------- |
| `l0/`     | Dea/L0 language, compiler, runtime, docs, examples, and tests |
| `tools/`  | Shared vendor dependencies and monorepo-level tooling         |

## Release Tags

Pre-monorepo history keeps its original bare tags. Existing legacy tags such as `v0.9.0`, `v0.9.1`, and older
`snapshot*` releases remain valid historical references and are not renamed.

Monorepo releases use level-prefixed tags only:

- L0 stable releases: `l0-vX.Y.Z`
- L0 snapshots: `l0-snapshot-...`
- Future L1 stable releases: `l1-vX.Y.Z`
- Future L1 snapshots: `l1-snapshot-...`

Bare `v*` tags are therefore a closed pre-monorepo namespace. New monorepo releases should not dual-tag with bare `v*`.

## Working In `l0/`

Dea/L0 works as a self-contained project inside [`l0/`](l0/). From the monorepo root, `cd l0` before running build,
test, or docs commands.

- Canonical project overview and quickstart: [`README.md`](README.md)
- L0 subtree pointer: [`l0/README.md`](l0/README.md)
- L0 contributor guidance: [`CONTRIBUTING.md`](CONTRIBUTING.md)
- L0 security policy: [`l0/SECURITY.md`](l0/SECURITY.md)
- L0 AI guidance: [`l0/CLAUDE.md`](l0/CLAUDE.md)

For example:

```bash
make venv   # shared by all level subtrees
cd l0
make help
make test-all
```

Third-party notices for shared vendored assets live at [`THIRD_PARTY_NOTICES`](THIRD_PARTY_NOTICES).
