# Feature Plan

## Migrate L1 public C ABI names from `l0_*` to `dea_*`

- Date: 2026-04-04
- Status: Draft
- Title: Migrate L1 public C ABI names from `l0_*` to `dea_*`
- Kind: Feature
- Severity: High
- Stage: 1
- Subsystem: Runtime / C emitter / generated C ABI / docs
- Modules:
  - `compiler/shared/runtime/l1_runtime.h`
  - `compiler/stage1_l0/src/c_emitter.l0`
  - `compiler/stage1_l0/tests/c_emitter_test.l0`
  - `compiler/stage1_l0/tests/backend_test.l0`
  - `compiler/stage1_l0/tests/fixtures/backend_golden/**`
  - `docs/reference/c-backend-design.md`
  - `docs/reference/design-decisions.md`
- Test modules:
  - `compiler/stage1_l0/tests/c_emitter_test.l0`
  - `compiler/stage1_l0/tests/backend_test.l0`
  - backend golden fixture refresh/verification
- Related:
  - `l1/work/plans/features/2026-04-04-l1-small-int-builtins-on-dea-abi-noref.md`
- Repro: `make test-stage1 TESTS="c_emitter_test backend_test"`

## Summary

L1 currently ships a copied bootstrap runtime and generated C surface that still expose historical `l0_*` names even
though they are no longer the intended language-facing ABI. The first step is to migrate that public C-facing surface to
`dea_*` consistently before adding more builtin scalar types.

This plan deliberately does not add new language features. It establishes a stable naming base so later work, including
new integer builtins, does not freeze a mixed ABI such as `l0_int` plus `l1_short`.

## Current State

1. `compiler/shared/runtime/l1_runtime.h` defines builtin scalar typedefs, optional wrappers, and public macros with
   `l0_*` / `L0_*` names.
2. `compiler/stage1_l0/src/c_emitter.l0` emits builtin C types, optional wrapper names, mangled user symbols, temps, and
   public guards with `l0_*` / `L0_*` spellings.
3. Emitter and backend tests, plus backend golden C fixtures, assert those historical spellings directly.
4. `docs/reference/c-backend-design.md` already describes the `l0_*` prefix as historical implementation detail rather
   than desired stable ABI.

## Defaults Chosen

1. `dea_*` is the stable forward-looking public C ABI prefix for Dea language/runtime surface.
2. `l1_*` is not introduced for public ABI names.
3. The migration covers all public names emitted into generated C, not just builtin typedefs.
4. `_rt_*` remains the internal runtime-helper namespace unless a helper name embeds a public type spelling that would
   otherwise leak `l0_*` into emitted C.
5. Temporary compatibility aliases for legacy `l0_*` names are provided only where they are centrally owned by
   `l1_runtime.h`; generated nominal names do not keep compatibility aliases.

## Goal

1. Make `dea_*` / `DEA_*` the primary public naming family for the L1 runtime header and generated C output.
2. Remove historical `l0_*` spellings from emitted builtin types, wrapper names, mangled generated identifiers, and
   public macros/guards.
3. Keep the migration behaviorally neutral: naming-only, no intended semantic change to Stage 1 language behavior.

## Implementation Phases

### Phase 1: Introduce `dea_*` runtime-owned names

Update `compiler/shared/runtime/l1_runtime.h` so the public runtime-owned types/macros are declared with `dea_*` /
`DEA_*` names first:

- builtin scalar typedefs such as `dea_bool`, `dea_byte`, `dea_int`, `dea_string`
- already-declared planned scalar typedefs such as `dea_tiny`, `dea_short`, `dea_ushort`
- runtime-owned optional wrapper typedefs such as `dea_opt_bool`, `dea_opt_byte`, `dea_opt_int`, `dea_opt_string`
- public constants/macros such as `DEA_STRING_CONST`, `DEA_UNREACHABLE`, and `DEA_DEFINED_*`

Add compatibility aliases in the same header for legacy runtime-owned `l0_*` spellings where feasible.

### Phase 2: Switch emitter output to `dea_*`

Update `compiler/stage1_l0/src/c_emitter.l0` so generated C uses the new public names consistently:

- builtin type lowering emits `dea_*`
- optional wrapper typedef names emit as `dea_opt_*`
- mangled structs, enums, functions, top-level lets, enum tags, and temporaries emit under `dea_...`
- public include/definition guards and string macros emit as `DEA_*`

Helpers that remain `_rt_*` internally should only be renamed when their current public spelling embeds `l0_*`, such as
checked narrow-cast helpers.

### Phase 3: Update tests, fixtures, and docs

Rewrite L1 emitter/backend tests and backend golden C fixtures to assert `dea_*` / `DEA_*` spellings.

Update backend/reference docs so they describe `dea_*` as the stable ABI and `l0_*` aliases, where present, as temporary
compatibility-only surface.

## Non-Goals

- adding new builtin language types
- changing type-checking or conversion rules
- changing runtime helper semantics beyond naming
- preserving compatibility aliases for generated per-module nominal names
- modifying L0 runtime or L0 generated C naming

## Verification Criteria

1. `make -C l1 test-stage1 TESTS="c_emitter_test"` passes with direct assertions on `dea_*` / `DEA_*` output.
2. `make -C l1 test-stage1 TESTS="backend_test"` passes with backend output and golden-fixture expectations updated to
   the new prefixes.
3. Generated C for existing Stage 1 programs contains no public `l0_*` or `L0_*` spellings except compatibility aliases
   defined inside `l1_runtime.h`.
4. The runtime header still provides centralized compatibility aliases for runtime-owned legacy names during the
   transition.

## Open Design Constraints

1. The migration must be prefix-complete for public emitted names; partial conversion would lock an inconsistent ABI.
2. Compatibility aliases must remain centralized in the runtime header rather than scattered through generated output.
3. Internal runtime implementation helpers may keep `_rt_*` names as long as emitted C no longer exposes legacy public
   type prefixes through their spellings.
