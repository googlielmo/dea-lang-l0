# L1 Stage 1 Compiler Seed

This directory contains the initial `stage1_l0` compiler seed for Dea/L1.

`stage1_l0` means the compiler is implemented in Dea/L0. It is seeded from the runnable Dea/L0 Stage 2 compiler and
retargeted to the Dea/L1 public interface.

The implementation sources in this subtree remain `.l0`, and the copied implementation test suite is also `.l0`. Those
tests are exercised through the upstream `l0c-stage2` bootstrap compiler rather than through `l1c` itself. The fixture
programs and copied L1 stdlib modules that those tests compile as L1-language inputs now use the `.l1` extension.

Run the local bootstrap workflow from [`l1/`](../../README.md):

```bash
make -C ../../l0 use-dev-stage2
make build-stage1
source build/l1/bin/l1-env.sh
l1c --version
```

For a non-default upstream bootstrap compiler, set `L1_BOOTSTRAP_L0C=/path/to/l0c-stage2` when running
`make build-stage1`.
