# The L0 Standard Library

The standard library provides safe, idiomatic wrappers around the low-level C runtime interface.

## Architecture Overview

```
┌─────────────────────────────────────────────────────────┐
│                      L0 User Code                       │
└─────────────────────────────────────────────────────────┘
                            │
                            ▼
┌─────────────────────────────────────────────────────────┐
│                      std.* Modules                      │
│   (io, string, optional, assert, rand, system, unit)    │
└─────────────────────────────────────────────────────────┘
                            │
                            ▼
┌─────────────────────────────────────────────────────────┐
│                      sys.* Modules                      │
│        sys.rt (safe FFI)  │  sys.unsafe (raw mem)       │
└─────────────────────────────────────────────────────────┘
                            │
                            ▼
┌─────────────────────────────────────────────────────────┐
│                 C Runtime (l0_runtime.h)                │
└─────────────────────────────────────────────────────────┘
```

The standard library is organized in two tiers.

- **`sys.*`** — Direct FFI bindings to the C runtime. These are `extern func` declarations with no L0 implementation.
  `sys.rt` provides safe primitives; `sys.unsafe` exposes raw memory operations.

- **`std.*`** — Pure L0 modules that wrap `sys.*` functions with ergonomic APIs, null-safety patterns, and
  domain-specific utilities.

## Module Reference

### `std.io` — Standard I/O

**Imports:** `sys.rt`, `std.unit`

Provides file I/O, standard input reading, output flushing, and formatted printing to stdout/stderr.

#### File I/O

| Function     | Signature                               | Description                                         |
|--------------|-----------------------------------------|-----------------------------------------------------|
| `read_file`  | `(path: string) -> string?`             | Read entire file contents. Returns `null` on error. |
| `write_file` | `(path: string, data: string) -> Unit?` | Write string to file. Returns `null` on error.      |

#### Standard Input

| Function           | Signature       | Description                                          |
|--------------------|-----------------|------------------------------------------------------|
| `read_line`        | `() -> string?` | Read a line from stdin. Returns `null` on EOF/error. |
| `read_char`        | `() -> int?`    | Read one character. Returns `null` on EOF/error.     |
| `read_char_or_eof` | `() -> int`     | Read one character. Returns `-1` on EOF/error.       |

#### Output Flushing

| Function       | Signature    | Description          |
|----------------|--------------|----------------------|
| `flush_stdout` | `() -> void` | Flush stdout buffer. |
| `flush_stderr` | `() -> void` | Flush stderr buffer. |

#### Printing (stdout)

Single-value prints:

| Function   | Signature             | Description              |
|------------|-----------------------|--------------------------|
| `printl`   | `() -> void`          | Print newline.           |
| `print_s`  | `(s: string) -> void` | Print string.            |
| `print_i`  | `(x: int) -> void`    | Print integer.           |
| `print_b`  | `(x: bool) -> void`   | Print boolean.           |
| `printl_s` | `(s: string) -> void` | Print string + newline.  |
| `printl_i` | `(x: int) -> void`    | Print integer + newline. |
| `printl_b` | `(x: bool) -> void`   | Print boolean + newline. |

Two-value prints (space-separated):

| Function                           | Signature                            |
|------------------------------------|--------------------------------------|
| `print_ss`, `print_si`, `print_sb` | `(a, b) -> void`                     |
| `print_is`, `print_ii`, `print_ib` | `(a, b) -> void`                     |
| `print_bs`, `print_bi`, `print_bb` | `(a, b) -> void`                     |
| `printl_ss`, `printl_si`, ...      | Same patterns with trailing newline. |

#### Printing (stderr)

Mirror of stdout functions with `err_` prefix:

| Function                                       | Signature            |
|------------------------------------------------|----------------------|
| `err_printl`                                   | `() -> void`         |
| `err_print_s`, `err_print_i`, `err_print_b`    | Single-value prints. |
| `err_printl_s`, `err_printl_i`, `err_printl_b` | With newline.        |
| `err_print_ss`, `err_print_si`, ...            | Two-value variants.  |

### `std.string` — String Operations

**Imports:** `sys.rt`

Provides basic string manipulation functions.

| Function    | Signature                                     | Description                                                      |
|-------------|-----------------------------------------------|------------------------------------------------------------------|
| `len_s`     | `(s: string) -> int`                          | Return string length in bytes.                                   |
| `char_at_s` | `(s: string, index: int) -> int`              | Return character code (0–255) at index. Panics on out-of-bounds. |
| `eq_s`      | `(a: string, b: string) -> bool`              | Compare two strings for equality.                                |
| `concat_s`  | `(a: string, b: string) -> string`            | Concatenate two strings (allocates new string).                  |
| `slice_s`   | `(s: string, start: int, end: int) -> string` | Return substring `[start, end)`. Panics on invalid bounds.       |

**Example:**

```l0
import std.string;
import std.io;

func example() -> void {
    let s: string = "hello";
    printl_i(len_s(s));           // 5
    printl_i(char_at_s(s, 0));    // 104 ('h')
    printl_s(concat_s(s, " world")); // "hello world"
    printl_s(slice_s(s, 1, 4));   // "ell"
}
```

### `std.optional` — Optional Value Utilities

**Imports:** `std.assert`

Provides helper functions for working with optional types (`T?`).

#### Unwrap with Default

| Function      | Signature                                   | Description              |
|---------------|---------------------------------------------|--------------------------|
| `unwrap_or_s` | `(opt: string?, default: string) -> string` | Return value or default. |
| `unwrap_or_i` | `(opt: int?, default: int) -> int`          | Return value or default. |
| `unwrap_or_b` | `(opt: bool?, default: bool) -> bool`       | Return value or default. |

#### Expect (Unwrap or Abort)

| Function   | Signature                               | Description                   |
|------------|-----------------------------------------|-------------------------------|
| `expect_s` | `(opt: string?, msg: string) -> string` | Unwrap or abort with message. |
| `expect_i` | `(opt: int?, msg: string) -> int`       | Unwrap or abort with message. |
| `expect_b` | `(opt: bool?, msg: string) -> bool`     | Unwrap or abort with message. |

**Example:**

```l0
import std.optional;
import std.io;

func example() -> void {
    let maybe_val: int? = null;
    let val: int = unwrap_or_i(maybe_val, 42);
    printl_i(val);  // 42
    
    let required: int? = 10 as int?;
    let x: int = expect_i(required, "value was null");
    printl_i(x);  // 10
}
```

### `std.unit` — Unit Type

The `Unit` type represents a value with no information, analogous to `void` but usable as a value type.

#### Type

```l0
struct Unit {}
```

#### Functions

| Function  | Signature     | Description                                                |
|-----------|---------------|------------------------------------------------------------|
| `unit`    | `() -> Unit`  | Return a `Unit` value.                                     |
| `present` | `() -> Unit?` | Return a non-null `Unit?` (useful for success indicators). |

**Use Case:** Functions that need to return "success or null" without payload:

```l0
import std.unit;
import std.io;

func try_operation() -> Unit? {
    let ok: bool = write_file("test.txt", "data") != null;
    if (ok) {
        return present();
    }
    return null;
}
```

### `std.assert` — Assertions

**Imports:** `sys.rt`

Provides runtime assertion for debugging and invariant checking.

| Function | Signature                           | Description                               |
|----------|-------------------------------------|-------------------------------------------|
| `assert` | `(cond: bool, msg: string) -> void` | Abort with message if condition is false. |

**Example:**

```l0
import std.assert;

func divide(a: int, b: int) -> int {
    assert(b != 0, "division by zero");
    return a / b;
}
```

### `std.rand` — Random Number Generation

**Imports:** `sys.rt`

Provides pseudo-random number generation utilities.

| Function         | Signature                         | Description                                 |
|------------------|-----------------------------------|---------------------------------------------|
| `rand_seed`      | `(seed: int) -> void`             | Seed the RNG. Pass `0` for time-based seed. |
| `rand_int`       | `(max: int) -> int`               | Random integer in `[0, max)`.               |
| `rand_int_range` | `(min: int, max: int) -> int`     | Random integer in `[min, max)`.             |
| `rand_bool`      | `() -> bool`                      | Random boolean.                             |
| `rand_dice`      | `(sides: int, rolls: int) -> int` | Sum of `rolls` dice with `sides` faces.     |

**Example:**

```l0
import std.rand;
import std.io;

func example() -> void {
    rand_seed(0);  // time-based seed
    printl_i(rand_int(100));        // 0–99
    printl_i(rand_int_range(10, 20)); // 10–19
    printl_b(rand_bool());          // true or false
    printl_i(rand_dice(6, 2));      // 2d6 roll (2–12)
}
```

### `std.system` — System Operations

**Imports:** `sys.rt`

Provides system-level functions for program control and environment access.

| Function  | Signature                       | Description                                                  |
|-----------|---------------------------------|--------------------------------------------------------------|
| `exit`    | `(code: int) -> void`           | Exit program with given code.                                |
| `env_get` | `(var_name: string) -> string?` | Get environment variable. Returns `null` if unset.           |
| `abort`   | `(message: string) -> void`     | Abort program with error message.                            |
| `errno`   | `() -> int`                     | Get last runtime error number.                               |
| `argc`    | `() -> int`                     | Get the number of command-line arguments.                    |
| `argv`    | `(index: int) -> string?`       | Get command-line argument at index. Panics if out-of-bounds. |

**Example:**

```l0
import std.system;
import std.io;
import std.optional;

func example() -> void {
    let home: string = unwrap_or_s(env_get("HOME"), "/tmp");
    printl_s(home);
    
    if (errno() != 0) {
        abort("unexpected error");
    }
    
    exit(0);
}
```

## Low-Level Runtime Modules

### `sys.rt` — Core Runtime FFI

This module declares `extern func` bindings to the C runtime. These are **safe** in the sense that they perform bounds
checking and handle errors gracefully.

**String Operations:**

- `rt_strlen`, `rt_string_get`, `rt_string_equals`
- `rt_string_concat`, `rt_string_slice`
- `rt_string_retain`, `rt_string_release` (reference counting)

**I/O Operations:**

- `rt_read_file_all`, `rt_write_file_all`
- `rt_print`, `rt_println`, `rt_print_int`, `rt_print_bool`
- `rt_print_stderr`, `rt_println_stderr`, etc.
- `rt_read_line`, `rt_read_char`
- `rt_flush_stdout`, `rt_flush_stderr`

**System Operations:**

- `rt_abort`, `rt_exit`
- `rt_srand`, `rt_rand`
- `rt_errno`, `rt_get_env_var`
- `rt_get_argc`, `rt_get_argv`

### `sys.unsafe` — Raw Memory Operations

This module exposes **unsafe** memory primitives. Misuse leads to undefined behavior.

| Function     | Signature                                        | Description            |
|--------------|--------------------------------------------------|------------------------|
| `rt_alloc`   | `(bytes: int) -> void*?`                         | Allocate raw memory.   |
| `rt_realloc` | `(ptr: void*, new_bytes: int) -> void*?`         | Resize allocation.     |
| `rt_free`    | `(ptr: void*) -> void`                           | Free memory.           |
| `rt_calloc`  | `(count: int, elem_size: int) -> void*?`         | Allocate zeroed array. |
| `rt_memcpy`  | `(dest: void*, src: void*, bytes: int) -> void*` | Copy memory.           |
| `rt_memset`  | `(dest: void*, value: int, bytes: int) -> void*` | Fill memory.           |

**Warning:** These functions do not perform bounds checking. Use only when implementing low-level data structures.

## Design Principles

1. **Null-safety via optionals:** Functions that can fail return `T?` rather than sentinel values. Use `std.optional`
   helpers or the `?` operator to handle them.

2. **No hidden allocations:** String operations like `concat_s` and `slice_s` explicitly allocate. The runtime manages
   string reference counting automatically.

3. **Explicit error handling:** The `errno()` function exposes the last runtime error. Check it after I/O operations if
   detailed error information is needed.

4. **Layered abstraction:** User code should prefer `std.*` modules. Direct use of `sys.rt` is acceptable for
   performance-critical code. Use of `sys.unsafe` should be reserved to higher-level abstractions and carefully audited.

5. **Monomorphic API:** Without generics, `std.optional` provides type-specific variants (`unwrap_or_s`, `unwrap_or_i`,
   etc.). This pattern will be replaced by generic functions in Stage 2.
