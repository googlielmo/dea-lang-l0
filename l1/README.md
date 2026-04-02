# Dea/L<sub>1</sub>

This subtree contains the bootstrap scaffold for Dea/L1 inside the Dea monorepo.

The root [README.md](../README.md) remains the canonical public landing page for now and stays L0-centered in this
phase. Run L1 bootstrap commands from this directory. L1-local documentation lives under [docs/](docs/).

The subtree also includes minimal example programs at [examples/](examples/).

At the moment the Dea/L1 source surface is `.l1`, including the copied L1 stdlib under `compiler/shared/l1/stdlib/` and
the L1-language fixture programs exercised by the bootstrap compiler tests. The `stage1_l0` compiler implementation and
its implementation tests are `.l0` sources and are built or run with the upstream `l0c-stage2` toolchain during
bootstrap.

Minimal local workflow:

```bash
make -C ../l0 use-dev-stage2
make build-stage1
source build/l1/bin/l1-env.sh
l1c --version
```

To use an explicit upstream L0 compiler instead of the repo-local default, set `L1_BOOTSTRAP_L0C=/path/to/l0c` when
running `make build-stage1`.
