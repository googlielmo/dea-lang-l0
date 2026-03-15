# Dea/L<sub>0</sub>

> _C-family syntax, UB-free semantics, ARC strings, sum types and pattern matching._

**L0 (Level Zero)** is a small systems language that compiles to C99. It is the foundational subset and first bootstrap
stage of the **Dea** language family.

Dea employs a staged compiler bootstrapping architecture (Level 0, Level 1, ..., Level N). Dea/L0 is now self-hosted; it
is the compiler base that will be used to compile L1. L1 will subsequently self-host to build L2, and the process will
repeat for successive levels.

The design is conservative by choice: a small, precisely specified language whose semantics leave no room for undefined
behavior. Operations are either well-defined or rejected - at compile time or with a named runtime error.

_Tertium non datur._

[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE-MIT)
[![License: Apache 2.0](https://img.shields.io/badge/License-Apache%202.0-blue.svg)](LICENSE-APACHE)

## Motivation

Writing a compiler is a systems programming task. You need to manage memory, represent complex data structures, and have
precise control over performance characteristics. Many modern languages either remove that kind of control or bury it
under runtime machinery.

Dea/L0 instead keeps a small, explicit core aimed at bootstrap-friendly implementation work. The objective is a small,
UB-free systems language sufficient to host its own compiler.

That constrains the design considerably. The type system needs sum types and pattern matching - a compiler without them
is fighting its own data. It needs explicit nullable types, because implicit null is a specification gap. It needs
deterministic resource management without requiring a garbage-collected runtime. It needs pointers without UB. It does
not need much else.

The surface syntax is C-family deliberately: operator precedence, braces, explicit types, `return`. Familiarity is
load-bearing when the language is also the implementation vehicle.

The C99 backend is a bootstrap convenience. The trusted C kernel isolates all platform-dependent behavior; the rest of
the semantics are enforced by L0 itself.

## Project status and directions

L0 is currently in its first self-hosted Stage 2 phase.

- Stage 1: complete and usable.

- Stage 2: lexer, parser, AST, name resolution, top-level signature resolution, local scope construction,
  expression/statement type checking, backend lowering, C emission, and direct `--build` / `--run` execution are
  implemented.

- Stage 2 `--gen`: implemented and parity-tested against Stage 1 on a committed golden corpus.

- Stage 2 bootstrap artifact: buildable today under `build/dea/bin` via `./scripts/build-stage2-l0c.sh`.

- Stage 2 repo-local Dea build workflow: available under `build/dea/bin` via `make install-dev-stages`;
  `make use-dev-stage2` prints the exact `source build/dea/bin/l0-env.sh` command after switching the alias.

- Stage 2 install prefix: available via `make PREFIX=/tmp/l0-install install`; this installs the self-hosted Stage 2
  compiler (`S1 -> S2`, then `S2 -> S2`) plus copied `shared/l0/stdlib` and `shared/runtime` assets.

- Stage 2 triple-bootstrap regression: available directly via `make triple-test`.

Today, Stage 2 implements `--check`, `--tok`, `--sym`, `--type`, deterministic `--gen`, and direct `--build` / `--run`.
The remaining public CLI gap is `--ast`, which is still NYI in Stage 2.

- **Built-in Observability:** Language developers need to know what memory is doing. L0 ships with native compiler flags
  to trace ARC events and allocations directly to stderr. Today these are fully usable through the Stage 1 driver and
  are already wired through Stage 2 `--gen`, `--build`, and `--run`:

```shell
l0c --run --trace-arc --trace-memory app.l0
```

## Design highlights

- `match` pattern-matches on enum variants, binding payload fields by name.
- `T?` is an explicit optional type. `expr?` short-circuits: if the expression is null, the enclosing `T?`-returning
  function returns null immediately.
- No exceptions.
- No `defer`: L0 uses `with` and `cleanup` blocks instead. Cleanup runs when the `with` body exits, the scoping is
  explicit, and there is nothing to reason about at a distance.
- No `goto`.
- `ptr.field` auto-dereferences; `->` is not a dereference operator (it is used for return type annotations).
- `=` is a statement. `if (x = 0)` is a type error.
- `case` dispatches on constant values (including strings): `"foobar" => stmt`, or `else stmt` for the default. No
  implicit fallthrough. Strings are valid case keys.
- `;` is not a valid empty statement. Use `null;` or an empty block if you need an explicit no-op.
- Widening conversions are implicit (`byte` to `int`, `T` to `T?`). Narrowing is always explicit and checked both
  statically and at runtime: `300 as byte` is a compiler error, `my_opt_str as string` panics on null. Use
  `unwrap_or_s(my_opt_str, "default")` if null is a valid case.

## Getting Started

### Prerequisites for Stage 1

- A C99 compiler (`gcc`, `clang`, and recent `tcc` version are known to work).
- `make` is the primary entrypoint for installation and development workflows.
- Python 3.14+.
- [`uv`](https://github.com/astral-sh/uv) (`make` will fall back to `python3 -m venv` if `uv` is not available).

#### Supported C compilers

The driver will use any C compiler specified in `$L0_CC` if set. Otherwise, it probes the system PATH for the first
available from this list:

- `tcc`
- `gcc`
- `clang`
- `cc`

The `$CC` environment variable will be checked as a last resort if none of the above are found.

If you need a specific compiler, set `$L0_CC` to its executable name or path. For example:

MSVC is supported by setting `$L0_CC` to point to `CL.EXE`, but it has not been tested (help wanted).

Specific versions of `gcc` and `clang` whose names include version numbers (e.g. `gcc-14`, `clang-22`) are not probed by
default but can be used by setting `$L0_CC` accordingly and will be recognized as such.

Tiny C Compiler (`tcc`) is the default if available, as it is fast and supports all required C99 features. It is
recommended to clone and build `tcc` from source if it is not available on your system, as some platform package
managers provide outdated versions.

### Install

Clone this repository and `cd` into it. Then create a virtual environment and install dependencies:

```shell
make venv                # create or reuse local .venv; prefers uv when available
```

For Windows-specific setup, generated launchers, MSYS2 bash usage, and native-shell (`cmd.exe` / PowerShell) usage, see
[README-WINDOWS.md](README-WINDOWS.md).

If you prefer to manage the environment manually, `uv sync --group dev --group docs` is the recommended direct command;
a plain `python3 -m venv .venv` workflow also works.

For an optional reproducible Linux test environment, use the explicit Docker wrapper:

```shell
make docker CMD=test-all
```

For normal developer use, install the repo-local switchable `l0c` alias, choose the stage you want, and source the
generated environment script:

```shell
make install-dev-stages
make use-dev-stage1      # or: make use-dev-stage2
source build/dea/bin/l0-env.sh
l0c --help
l0c --version
```

The `./scripts/l0c` entrypoint remains available, but it is the source-tree Stage 1 wrapper and is mainly useful for
bootstrap mechanics, internal tooling, and Stage 1-focused testing.

For a repo-independent Stage 2 install prefix:

```shell
make PREFIX=/tmp/l0-install install
source /tmp/l0-install/bin/l0-env.sh
l0c --version
```

`make install` requires an explicit `PREFIX=...`; there is no implicit default install root.

`install` installs the self-hosted Stage 2 compiler (`Compiler 2` from the triple-bootstrap chain), not the initial
Stage 1-built bootstrap artifact.

### First program

```l0
module hello;

import std.io;

func main() -> int {
    printl_s("Hello, L0!");
    return 0;
}
```

```shell
l0c hello.l0 -o hello && ./hello        # produce a binary and run it
l0c --run hello.l0                      # compile and execute in one step
l0c --check hello.l0                    # analyze only, no output (use `-v`/`-vvv` for verbose diagnostics)
l0c --version                           # print the active compiler stage identity and exit
```

### Multi-module projects

```shell
l0c --run -P ./src -P ./lib main        # -P adds a project root to search for modules; main is the target module (main.l0)
```

The compiler resolves modules from system roots (stdlib) then project roots in order.

Environment-variable defaults and launcher-specific path behavior are documented in
[compiler/stage2_l0/README.md](compiler/stage2_l0/README.md),
[docs/reference/project-status.md](docs/reference/project-status.md), and [README-WINDOWS.md](README-WINDOWS.md).

### Examples

```shell
l0c -P examples --run hamurabi
```

The `examples/` directory covers most language features and is worth reading as code.

[Hamurabi](examples/hamurabi.l0) is a faithful L0 port of the 1968 resource-management game - ancient Sumeria, grain
storage, and all.

### A more advanced example

<details>
<summary>A simple prefix notation calculator</summary>
<p>

```l0
module demo;

import std.io;
import std.string;
import std.text;
import std.system;

// A simple expression language with integers, addition, and multiplication.
enum Expr {
    Num(value: int);
    Add(left: Expr*, right: Expr*);
    Mul(left: Expr*, right: Expr*);
}

struct Cursor { pos: int; } // current position in argv

/* Recursively evaluate an expression tree. */
func eval(e: Expr*) -> int {
    match (*e) {
        Num(value)       => { return value; }
        Add(left, right) => { return eval(left) + eval(right); }
        Mul(left, right) => { return eval(left) * eval(right); }
    }
}

/* Recursively free an expression tree. */
func free_expr(e: Expr*?) {
    if (e == null) return;
    match (*(e as Expr*)) { // unwrap
        Num(value)       => {}
        Add(left, right) => { free_expr(left); free_expr(right); }
        Mul(left, right) => { free_expr(left); free_expr(right); }
    }
    drop e;
}

/* A simple recursive-descent parser for our expression language.
   Returns null on bad input; ? propagates failure upward. */
func parse(c: Cursor*) -> Expr*? {
    if (c.pos >= argc()) { return null; }

    let tok: string = argv(c.pos);
    c.pos = c.pos + 1;

    let n: int? = string_to_int(tok);
    if (n != null) { return new Num(n as int); }

    let result: Expr*? = null;
    with (let left: Expr*? = parse(c)?,
          let right: Expr*? = parse(c)?) {
        case (tok) {
            "add" => { result = new Add(left as Expr*, right as Expr*); }
            "mul" => { result = new Mul(left as Expr*, right as Expr*); }
            // unrecognized operator: leave result as null to signal failure
        }
        return result;
    }
    cleanup {
        if (result == null) { // on parse failure, free any subtrees we allocated
            free_expr(left);
            free_expr(right);
        }
    }
}

/* Main entry point. Expects prefix-notation arguments:
   demo add 2 3          # prints "= 5"
   demo mul 6 add 5 2    # prints "= 42" */
func main() -> int {
    with (let c = new Cursor(1) => drop c,
          let expr = parse(c) => free_expr(expr)) { // release c and expr on exit
        if (expr == null || c.pos != argc()) {
            printl_s("usage: demo <expr>\n<expr> ::= add|mul <expr> <expr> | <int>");
            return 1;
        }
        printl_si("=", eval(expr as Expr*)); // unwrap
        return 0;
    }
}
```

</details>

This program is available in [examples/demo.l0](examples/demo.l0). You can run it from the repository root as follows:

```shell
l0c examples/demo.l0 -o demo
./demo mul 6 add 5 2 
```

It will parse the expression `mul 6 add 5 2` as a tree, evaluate it to `6 * (5 + 2)`, and print `= 42`.

## Language overview

**Types:** `int`, `bool`, `string`, `byte`, structs, enums with payloads, pointers (`T*`, `T**`), nullable pointers
(`T*?`), optional values (`T?`), type aliases.

`string` is a convenient, small value type: you can assign it, pass it, and return it cheaply. String memory (where the
expensive data is stored) is managed automatically via reference counting.

Manual heap allocation of structs and other data in the language is explicit (`new`/`drop`) and delegated to the
programmer (no GC).

`sizeof()` and `ord()` are language intrinsics that return the size of a type in bytes and the ordinal value of an enum
variant, respectively.

**Modules:** one file, one module. Dotted names (`std.io`). No forward declarations - all top-level symbols in a module
are visible throughout it. Symbols are qualified as `module::Symbol` where disambiguation is needed.

**Pointers:** `T*` is non-null. `T*?` is nullable. No `&` address-of operator in current stages. No pointer arithmetic
in Stage 1. Field access auto-dereferences.

**Null safety:** `T?` for optional values; `null` for the empty case. `T` widens to `T?` implicitly. `T? as T` narrows
with a runtime panic on null; use `unwrap_or_*` variants when null is a valid case. `expr?` propagates null from the
enclosing function.

**No UB:** every operation is defined, rejected at compile time, or produces a named runtime failure. No implicit
narrowing conversions. No assignment-as-expression.

**Extern:** `extern` functions interface directly with the C kernel.

**Control flow:** `if`/`else`, `while`, C-style `for`, `return`, `break`, `continue`, `match` (enum variant dispatch),
`case` (literal dispatch), `with`/`cleanup` (scoped resource management), `expr?` (null propagation).

## Grammar

The authoritative grammar is in [docs/reference/grammar/l0.md](docs/reference/grammar/l0.md).

Types compose as: `T*`, `T**`, `T?`, `T*?`. Expressions follow C precedence, extended with the postfix `?` operator and
`as` casts.

## Compiler implementation architecture

Stage 1 follows a conventional pipeline from lexer to semantic analysis to C99 code generation. Stage 2 mirrors the same
pipeline in L0 itself, with separate lexer, parser, AST, type-checking, backend, and driver modules.

For the full compiler workflow, bootstrap/install layout, test targets, and current Stage 2 command surface, use:

References:

- [Architecture and data flow](docs/reference/architecture.md)
- [Design decisions](docs/reference/design-decisions.md)
- [Ownership and memory management](docs/reference/ownership.md)
- [Stage 1 contract](docs/specs/compiler/stage1-contract.md)
- [Shared CLI contract](docs/specs/compiler/cli-contract.md)

## CLI

The recommended developer-facing CLI is `l0c` after selecting a stage with `make use-dev-stage1` or
`make use-dev-stage2` and sourcing `build/dea/bin/l0-env.sh`. The source-tree `./scripts/l0c` wrapper is Stage 1 only
and remains useful mainly for bootstrap mechanics and Stage 1-focused testing.

```shell
l0c [mode] [options] <target>
# or, for the source-tree Stage 1 wrapper only:
# ./scripts/l0c [mode] [options] <target>
```

Global identity and logging options include `--help`, `--version`, `-v/--verbose`, and `-l/--log`.

| Mode           | Action                          |
| -------------- | ------------------------------- |
| `--build`      | Compile to binary (default)     |
| `--run` / `-r` | Compile and execute             |
| `--gen` / `-g` | Emit C99                        |
| `--check`      | Analyze only                    |
| `--ast`        | Dump AST (Stage 1; Stage 2 NYI) |
| `--sym`        | Dump module symbols             |
| `--type`       | Dump resolved types             |
| `--tok`        | Dump token stream               |

```shell
l0c --build --keep-c hello.l0             # retain the generated C
l0c --run app.main -- arg1 arg2           # pass arguments to the program
l0c --run --trace-arc --trace-memory app  # trace ARC and allocation to stderr
l0c -c clang -C "-Og -DDEBUG" hello.l0    # use a specific C compiler with custom flags
```

Trace output contract: [docs/specs/runtime/trace.md](docs/specs/runtime/trace.md).

Full CLI contract — mode flags, options, targets, identity strings, exit codes, and stage-specific differences:
[docs/specs/compiler/cli-contract.md](docs/specs/compiler/cli-contract.md).

## Project status

[docs/reference/project-status.md](docs/reference/project-status.md).

## Contributing

See [CONTRIBUTING.md](CONTRIBUTING.md).

## License

[MIT](LICENSE-MIT) or [Apache 2.0](LICENSE-APACHE), at your option.

Third-party notices: [`THIRD_PARTY_NOTICES`](THIRD_PARTY_NOTICES).

## Author

`gwz` ([@googlielmo](https://github.com/googlielmo)).
