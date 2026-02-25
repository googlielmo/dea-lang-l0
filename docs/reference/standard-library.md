# The L0 Standard Library

The standard library provides ergonomic L0 modules (`std.*`) and low-level runtime bindings (`sys.*`).

For canonical ownership behavior around `new`/`drop`, ARC strings, and container-specific retain/release patterns, see
[ownership.md](ownership.md).

## Architecture Overview

```
┌─────────────────────────────────────────────────────────┐
│                      L0 User Code                       │
└─────────────────────────────────────────────────────────┘
                             │
                             ▼
┌─────────────────────────────────────────────────────────┐
│                      std.* Modules                      │
│ array, assert, hashmap, hashset, io, linear_map, math,  │
│ optional, rand, string, system, text, unit, vector      │
└─────────────────────────────────────────────────────────┘
                             │
                             ▼
┌─────────────────────────────────────────────────────────┐
│                      sys.* Modules                      │
│      hash, rt (runtime API), unsafe (raw mem)           │
└─────────────────────────────────────────────────────────┘
                             │
                             ▼
┌─────────────────────────────────────────────────────────┐
│                 C Runtime (l0_runtime.h)                │
└─────────────────────────────────────────────────────────┘
```

## Module Reference

### `std.assert`

**Imports:** `sys.rt`

| Function | Signature                           | Description                             |
|----------|-------------------------------------|-----------------------------------------|
| `assert` | `(cond: bool, msg: string) -> void` | Aborts with `msg` when `cond` is false. |

### `std.array`

**Imports:** `sys.rt`, `sys.unsafe`, `std.assert`, `std.string`

| Type/Function | Signature                                                             | Description                                        |
|---------------|-----------------------------------------------------------------------|----------------------------------------------------|
| `ArrayBase`   | `struct ArrayBase { capacity: int; element_size: int; data: void*; }` | Untyped fixed-size backing storage.                |
| `arr_create`  | `(element_size: int, length: int) -> ArrayBase*`                      | Allocates and zero-initializes storage.            |
| `arr_check`   | `(self: ArrayBase*, index: int) -> void`                              | Bounds-check helper (`0 <= index < capacity`).     |
| `arr_resize`  | `(self: ArrayBase*, new_length: int) -> void`                         | Reallocates backing storage and zero-fills growth. |
| `arr_get`     | `(self: ArrayBase*, index: int) -> void*`                             | Returns element pointer at index.                  |
| `arr_zap`     | `(self: ArrayBase*, index: int) -> void`                              | Zeroes one element slot.                           |
| `arr_free`    | `(self: ArrayBase*) -> void`                                          | Frees backing storage and drops container.         |

### `std.vector`

**Imports:** `sys.rt`, `sys.unsafe`, `std.assert`, `std.string`, `std.array`

| Type/Function                | Signature                                                   | Description                                     |
|------------------------------|-------------------------------------------------------------|-------------------------------------------------|
| `VectorBase`                 | `struct VectorBase { arr: ArrayBase*; length: int; }`       | Untyped growable vector.                        |
| `vec_create`                 | `(element_size: int, initial_capacity: int) -> VectorBase*` | Creates vector storage.                         |
| `vec_grow`                   | `(self: VectorBase*) -> void`                               | Ensures capacity and increments length.         |
| `vec_reserve`                | `(self: VectorBase*, total_capacity: int) -> void`          | Ensures at least requested capacity.            |
| `vec_get`                    | `(self: VectorBase*, index: int) -> void*`                  | Returns element pointer.                        |
| `vec_push`                   | `(self: VectorBase*) -> void*`                              | Grows and returns pointer to new slot.          |
| `vec_size`                   | `(self: VectorBase*) -> int`                                | Returns logical length.                         |
| `vec_capacity`               | `(self: VectorBase*) -> int`                                | Returns current capacity.                       |
| `vec_clear`                  | `(self: VectorBase*) -> void`                               | Clears vector and resets backing capacity to 1. |
| `vec_free`                   | `(self: VectorBase*) -> void`                               | Frees vector storage.                           |
| `vec_push_int/byte/bool/ptr` | typed push helpers                                          | Push typed scalar/pointer values.               |
| `vi_sort`                    | `(self: VectorBase*) -> void`                               | Insertion sort for `int` vectors (ascending).   |
| `VectorString`               | `type VectorString = VectorBase`                            | String-specialized vector alias.                |
| `vs_*`                       | `vs_create/push/get/size/capacity/sort/clear/free`          | String vector API with ARC-aware clear/free.    |

### `std.hashmap`

**Imports:** `sys.rt`, `sys.unsafe`, `std.assert`, `std.string`, `sys.hash`, `std.array`, `std.vector`

| Type/Function                     | Signature                                | Description                                  |
|-----------------------------------|------------------------------------------|----------------------------------------------|
| `StringPtrMap`                    | `struct`                                 | Open-addressed `string -> void*` map.        |
| `spm_create/create_with_capacity` | constructors                             | Create map with default or minimum capacity. |
| `spm_put/get/has/remove`          | map ops                                  | Insert/update/lookup/presence/remove.        |
| `spm_size/capacity/clear/free`    | management                               | Size, capacity, clear entries, free map.     |
| `spm_keys`                        | `(self: StringPtrMap*) -> VectorString*` | Returns keys as new string vector.           |
| `spm_slot_occupied/key/value`     | iteration helpers                        | Slot-level iteration support.                |
| `StringIntMap`                    | `struct`                                 | Open-addressed `string -> int` map.          |
| `sim_create/create_with_capacity` | constructors                             | Create map with default or minimum capacity. |
| `sim_put/get/has/remove`          | map ops                                  | Insert/update/lookup/presence/remove.        |
| `sim_size/capacity/clear/free`    | management                               | Size, capacity, clear entries, free map.     |
| `sim_keys`                        | `(self: StringIntMap*) -> VectorString*` | Returns keys as new string vector.           |
| `sim_slot_occupied/key/value`     | iteration helpers                        | Slot-level iteration support.                |

### `std.hashset`

**Imports:** `sys.rt`, `sys.unsafe`, `std.assert`, `std.string`, `sys.hash`, `std.array`, `std.vector`

| Type/Function                    | Signature                                 | Description                                  |
|----------------------------------|-------------------------------------------|----------------------------------------------|
| `StringSet`                      | `struct`                                  | Open-addressed set of strings.               |
| `ss_create/create_with_capacity` | constructors                              | Create set with default or minimum capacity. |
| `ss_add`                         | `(self: StringSet*, key: string) -> bool` | Adds key; returns false if already present.  |
| `ss_has/remove`                  | set ops                                   | Presence check and removal.                  |
| `ss_size/capacity/clear/free`    | management                                | Size, capacity, clear entries, free set.     |
| `ss_to_vector`                   | `(self: StringSet*) -> VectorString*`     | Returns elements as new vector.              |
| `ss_slot_occupied/key`           | iteration helpers                         | Slot-level iteration support.                |

### `std.linear_map`

**Imports:** `sys.rt`, `sys.unsafe`, `std.assert`, `std.string`, `sys.hash`, `std.vector`

| Type/Function           | Signature                                                 | Description                                 |
|-------------------------|-----------------------------------------------------------|---------------------------------------------|
| `LinearMapBase`         | `struct`                                                  | Generic byte-comparison linear map storage. |
| `lm_create/free/len`    | base lifecycle                                            | Create, free, and query length.             |
| `lm_set/get/remove`     | base ops                                                  | Set/get/remove key-value by raw key bytes.  |
| `lm_contains_key/value` | base queries                                              | Presence checks by key/value bytes.         |
| `LinearMapStringString` | `struct`                                                  | `string -> string` specialization.          |
| `lmss_*`                | `create/free/len/set/get/contains/remove/key_at/value_at` | ARC-aware string map API.                   |
| `LinearMapIntString`    | `struct`                                                  | `int -> string` specialization.             |
| `lmis_*`                | `create/free/len/set/get/contains/remove/key_at/value_at` | ARC-aware int/string map API.               |

### `sys.hash`

This module exposes runtime hash functions directly via `extern func` declarations.

| Function             | Signature                         | Description                      |
|----------------------|-----------------------------------|----------------------------------|
| `rt_hash_bool`       | `(value: bool) -> int`            | Hashes `bool`.                   |
| `rt_hash_byte`       | `(value: byte) -> int`            | Hashes `byte`.                   |
| `rt_hash_int`        | `(value: int) -> int`             | Hashes `int`.                    |
| `rt_hash_string`     | `(value: string) -> int`          | Hashes `string`.                 |
| `rt_hash_data`       | `(data: void*, size: int) -> int` | Hashes raw bytes at pointer.     |
| `rt_hash_opt_bool`   | `(opt: bool?) -> int`             | Hashes optional `bool`.          |
| `rt_hash_opt_byte`   | `(opt: byte?) -> int`             | Hashes optional `byte`.          |
| `rt_hash_opt_int`    | `(opt: int?) -> int`              | Hashes optional `int`.           |
| `rt_hash_opt_string` | `(opt: string?) -> int`           | Hashes optional `string`.        |
| `rt_hash_ptr`        | `(ptr: void*) -> int`             | Hashes pointer address.          |
| `rt_hash_opt_ptr`    | `(opt: void*?) -> int`            | Hashes optional pointer address. |

### `std.io`

**Imports:** `sys.rt`, `std.unit`

`std.io` classifies I/O success/failure from direct runtime return values (optional/boolean/sentinel results).

| Function           | Signature                               | Description                                 |
|--------------------|-----------------------------------------|---------------------------------------------|
| `read_file`        | `(path: string) -> string?`             | Reads entire file; `null` on error.         |
| `write_file`       | `(path: string, data: string) -> Unit?` | Writes entire file; `null` on error.        |
| `read_line`        | `() -> string?`                         | Reads line from stdin; `null` on EOF/error. |
| `read_char`        | `() -> int?`                            | Reads one byte as int; `null` on EOF/error. |
| `read_char_or_eof` | `() -> int`                             | Reads one byte; returns `-1` on EOF/error.  |
| `flush_stdout`     | `() -> void`                            | Flushes stdout.                             |
| `flush_stderr`     | `() -> void`                            | Flushes stderr.                             |
| `printl`           | `() -> void`                            | Prints newline to stdout.                   |
| `print_s`          | `(s: string) -> void`                   | Prints string to stdout.                    |
| `print_i`          | `(x: int) -> void`                      | Prints int to stdout.                       |
| `print_b`          | `(x: bool) -> void`                     | Prints bool to stdout.                      |
| `printl_s`         | `(s: string) -> void`                   | Prints string + newline to stdout.          |
| `printl_i`         | `(x: int) -> void`                      | Prints int + newline to stdout.             |
| `printl_b`         | `(x: bool) -> void`                     | Prints bool + newline to stdout.            |
| `print_ss`         | `(s1: string, s2: string) -> void`      | Prints two values separated by space.       |
| `print_si`         | `(s: string, x: int) -> void`           | Prints two values separated by space.       |
| `print_sb`         | `(s: string, b: bool) -> void`          | Prints two values separated by space.       |
| `print_is`         | `(x: int, s: string) -> void`           | Prints two values separated by space.       |
| `print_ii`         | `(x1: int, x2: int) -> void`            | Prints two values separated by space.       |
| `print_ib`         | `(x: int, b: bool) -> void`             | Prints two values separated by space.       |
| `print_bs`         | `(b: bool, s: string) -> void`          | Prints two values separated by space.       |
| `print_bi`         | `(b: bool, x: int) -> void`             | Prints two values separated by space.       |
| `print_bb`         | `(b1: bool, b2: bool) -> void`          | Prints two values separated by space.       |
| `printl_ss`        | `(s1: string, s2: string) -> void`      | `print_ss` + newline.                       |
| `printl_si`        | `(s: string, x: int) -> void`           | `print_si` + newline.                       |
| `printl_sb`        | `(s: string, b: bool) -> void`          | `print_sb` + newline.                       |
| `printl_is`        | `(x: int, s: string) -> void`           | `print_is` + newline.                       |
| `printl_ii`        | `(x1: int, x2: int) -> void`            | `print_ii` + newline.                       |
| `printl_ib`        | `(x: int, b: bool) -> void`             | `print_ib` + newline.                       |
| `printl_bs`        | `(b: bool, s: string) -> void`          | `print_bs` + newline.                       |
| `printl_bi`        | `(b: bool, x: int) -> void`             | `print_bi` + newline.                       |
| `printl_bb`        | `(b1: bool, b2: bool) -> void`          | `print_bb` + newline.                       |
| `err_printl`       | `() -> void`                            | Prints newline to stderr.                   |
| `err_print_s`      | `(s: string) -> void`                   | Prints string to stderr.                    |
| `err_print_i`      | `(x: int) -> void`                      | Prints int to stderr.                       |
| `err_print_b`      | `(x: bool) -> void`                     | Prints bool to stderr.                      |
| `err_printl_s`     | `(s: string) -> void`                   | Prints string + newline to stderr.          |
| `err_printl_i`     | `(x: int) -> void`                      | Prints int + newline to stderr.             |
| `err_printl_b`     | `(x: bool) -> void`                     | Prints bool + newline to stderr.            |
| `err_print_ss`     | `(s1: string, s2: string) -> void`      | Prints two values separated by space.       |
| `err_print_si`     | `(s: string, x: int) -> void`           | Prints two values separated by space.       |
| `err_print_sb`     | `(s: string, b: bool) -> void`          | Prints two values separated by space.       |
| `err_print_is`     | `(x: int, s: string) -> void`           | Prints two values separated by space.       |
| `err_print_ii`     | `(x1: int, x2: int) -> void`            | Prints two values separated by space.       |
| `err_print_ib`     | `(x: int, b: bool) -> void`             | Prints two values separated by space.       |
| `err_print_bs`     | `(b: bool, s: string) -> void`          | Prints two values separated by space.       |
| `err_print_bi`     | `(b: bool, x: int) -> void`             | Prints two values separated by space.       |
| `err_print_bb`     | `(b1: bool, b2: bool) -> void`          | Prints two values separated by space.       |

### `std.math`

**Imports:** `std.assert`

| Function | Signature                 | Description                                                             |
|----------|---------------------------|-------------------------------------------------------------------------|
| `emod`   | `(a: int, b: int) -> int` | Euclidean modulo. Requires `b > 0`; always returns non-negative result. |

### `std.optional`

**Imports:** `std.assert`

| Function      | Signature                                   | Description                           |
|---------------|---------------------------------------------|---------------------------------------|
| `unwrap_or_s` | `(opt: string?, default: string) -> string` | Returns value or default.             |
| `unwrap_or_i` | `(opt: int?, default: int) -> int`          | Returns value or default.             |
| `unwrap_or_b` | `(opt: bool?, default: bool) -> bool`       | Returns value or default.             |
| `expect_s`    | `(opt: string?, msg: string) -> string`     | Returns value or aborts with message. |
| `expect_i`    | `(opt: int?, msg: string) -> int`           | Returns value or aborts with message. |
| `expect_b`    | `(opt: bool?, msg: string) -> bool`         | Returns value or aborts with message. |

### `std.rand`

**Imports:** `sys.rt`

| Function         | Signature                         | Description                                           |
|------------------|-----------------------------------|-------------------------------------------------------|
| `rand_seed`      | `(seed: int) -> void`             | Seeds RNG. `0` selects time-based seed.               |
| `rand_int`       | `(max: int) -> int`               | Returns random int in `[0, max)`.                     |
| `rand_int_range` | `(min: int, max: int) -> int`     | Returns random int in `[min, max)`.                   |
| `rand_bool`      | `() -> bool`                      | Returns random bool.                                  |
| `rand_dice`      | `(sides: int, rolls: int) -> int` | Rolls `rolls` dice of `sides` sides and sums results. |

### `std.string`

**Imports:** `sys.rt`, `std.assert`

| Function        | Signature                                             | Description                                                             |
|-----------------|-------------------------------------------------------|-------------------------------------------------------------------------|
| `len_s`         | `(s: string) -> int`                                  | Returns string byte length.                                             |
| `char_at_s`     | `(s: string, index: int) -> byte`                     | Returns byte at index.                                                  |
| `eq_s`          | `(a: string, b: string) -> bool`                      | Compares strings for equality.                                          |
| `cmp_s`         | `(a: string, b: string) -> int`                       | Compares strings lexicographically (`<0`, `0`, `>0`).                   |
| `concat_s`      | `(a: string, b: string) -> string`                    | Concatenates strings.                                                   |
| `slice_s`       | `(s: string, start: int, end: int) -> string`         | Returns substring `[start, end)`.                                       |
| `byte_to_s`     | `(b: byte) -> string`                                 | Creates one-byte string.                                                |
| `bytes_to_s`    | `(bytes: byte*, len: int) -> string`                  | Creates string from byte buffer.                                        |
| `find_s`        | `(haystack: string, needle: string) -> int`           | Returns first match index or `-1`.                                      |
| `find_from_s`   | `(haystack: string, needle: string, pos: int) -> int` | Returns first match index at/after `pos`, or `-1`. Requires `pos >= 0`. |
| `contains_s`    | `(haystack: string, needle: string) -> bool`          | Returns whether `needle` occurs in `haystack`.                          |
| `starts_with_s` | `(s: string, prefix: string) -> bool`                 | Returns whether `s` starts with `prefix`.                               |
| `ends_with_s`   | `(s: string, suffix: string) -> bool`                 | Returns whether `s` ends with `suffix`.                                 |

### `std.text`

**Imports:** `std.string`, `std.math`, `std.assert`, `std.vector`

| Type/Function                                       | Signature                                                                                           | Description                                         |
|-----------------------------------------------------|-----------------------------------------------------------------------------------------------------|-----------------------------------------------------|
| `StringBuffer`                                      | `struct`                                                                                            | String-part buffer with cached total size.          |
| `sb_*`                                              | `create/append/append_int/append_byte/to_string/size/free`                                          | String buffer API.                                  |
| `CharBuffer`                                        | `struct`                                                                                            | Byte-backed buffer for incremental string assembly. |
| `cb_*`                                              | `create/capacity/size/reserve/append/append_s/append_slice/append_int/reverse/to_string/clear/free` | Char buffer API.                                    |
| `concat3_s/concat4_s`                               | string concat helpers                                                                               | Concatenate 3 or 4 strings efficiently.             |
| `to_upper_s/to_lower_s`                             | case helpers                                                                                        | Convert full string case.                           |
| `repeat_s/reverse_s`                                | string helpers                                                                                      | Repeat or reverse string content.                   |
| `int_to_string_base`                                | `(value: int, base: int) -> string`                                                                 | Base conversion for signed ints (`2..16`).          |
| `int_to_string/int_to_hex_string/int_to_bin_string` | format helpers                                                                                      | Decimal, hex, and binary formatting helpers.        |

### `std.system`

**Imports:** `sys.rt`

| Function  | Signature                       | Description                                    |
|-----------|---------------------------------|------------------------------------------------|
| `exit`    | `(code: int) -> void`           | Exits program with status code.                |
| `env_get` | `(var_name: string) -> string?` | Returns environment variable or `null`.        |
| `argc`    | `() -> int`                     | Returns command-line argument count.           |
| `argv`    | `(index: int) -> string`        | Returns command-line argument string at index. |
| `abort`   | `(message: string) -> void`     | Aborts program with message.                   |
| `errno`   | `() -> int`                     | Returns runtime error number.                  |

### `std.unit`

| Type/Function | Signature        | Description                     |
|---------------|------------------|---------------------------------|
| `Unit`        | `struct Unit {}` | Unit type.                      |
| `unit`        | `() -> Unit`     | Returns unit value.             |
| `present`     | `() -> Unit?`    | Returns non-null optional unit. |

### `sys.rt`

Low-level runtime FFI for strings, I/O, process/system, and errors.

### `sys.unsafe`

Low-level raw memory FFI. Misuse can cause undefined behavior.

## FFI Inventory (`extern func`)

All `extern func` symbols exposed to L0 from stdlib modules are listed here.

### Declared in `sys.rt` (35)

| Function                    | Signature                                     |
|-----------------------------|-----------------------------------------------|
| `rt_string_get`             | `(s: string, index: int) -> byte`             |
| `rt_strlen`                 | `(str: string) -> int`                        |
| `rt_string_equals`          | `(a: string, b: string) -> bool`              |
| `rt_string_compare`         | `(a: string, b: string) -> int`               |
| `rt_string_concat`          | `(a: string, b: string) -> string`            |
| `rt_string_slice`           | `(s: string, start: int, end: int) -> string` |
| `rt_string_from_byte_array` | `(bytes: byte*, len: int) -> string`          |
| `rt_string_from_byte`       | `(b: byte) -> string`                         |
| `rt_string_retain`          | `(s: string) -> void`                         |
| `rt_string_release`         | `(s: string) -> void`                         |
| `rt_read_file_all`          | `(path: string) -> string?`                   |
| `rt_write_file_all`         | `(path: string, data: string) -> bool`        |
| `rt_flush_stdout`           | `() -> void`                                  |
| `rt_flush_stderr`           | `() -> void`                                  |
| `rt_print`                  | `(s: string) -> void`                         |
| `rt_print_stderr`           | `(s: string) -> void`                         |
| `rt_println`                | `() -> void`                                  |
| `rt_println_stderr`         | `() -> void`                                  |
| `rt_print_int`              | `(x: int) -> void`                            |
| `rt_print_int_stderr`       | `(x: int) -> void`                            |
| `rt_print_bool`             | `(x: bool) -> void`                           |
| `rt_print_bool_stderr`      | `(x: bool) -> void`                           |
| `rt_read_line`              | `() -> string?`                               |
| `rt_read_char`              | `() -> int`                                   |
| `rt_abort`                  | `(message: string) -> void`                   |
| `rt_exit`                   | `(code: int) -> void`                         |
| `rt_srand`                  | `(seed: int) -> void`                         |
| `rt_rand`                   | `(max: int) -> int`                           |
| `rt_errno`                  | `() -> int`                                   |
| `rt_get_env_var`            | `(name: string) -> string?`                   |
| `rt_get_argc`               | `() -> int`                                   |
| `rt_get_argv`               | `(i: int) -> string`                          |
| `rt_system`                 | `(cmd: string) -> int`                        |
| `rt_file_exists`            | `(path: string) -> bool`                      |
| `rt_delete_file`            | `(path: string) -> bool`                      |

### Declared in `sys.unsafe` (8)

These are unsafe raw-memory primitives.

| Function           | Signature                                                     |
|--------------------|---------------------------------------------------------------|
| `rt_alloc`         | `(bytes: int) -> void*?`                                      |
| `rt_realloc`       | `(ptr: void*, new_bytes: int) -> void*?`                      |
| `rt_free`          | `(ptr: void*?) -> void`                                       |
| `rt_calloc`        | `(count: int, elem_size: int) -> void*?`                      |
| `rt_memcpy`        | `(dest: void*, src: void*, bytes: int) -> void*`              |
| `rt_memset`        | `(dest: void*, value: int, bytes: int) -> void*`              |
| `rt_memcmp`        | `(a: void*, b: void*, bytes: int) -> int`                     |
| `rt_array_element` | `(array_data: void*, element_size: int, index: int) -> void*` |

### Declared in `sys.hash` (11)

These are runtime-backed hash externs declared directly in `sys.hash`.

| Function             | Signature                         |
|----------------------|-----------------------------------|
| `rt_hash_bool`       | `(value: bool) -> int`            |
| `rt_hash_byte`       | `(value: byte) -> int`            |
| `rt_hash_int`        | `(value: int) -> int`             |
| `rt_hash_string`     | `(value: string) -> int`          |
| `rt_hash_data`       | `(data: void*, size: int) -> int` |
| `rt_hash_opt_bool`   | `(opt: bool?) -> int`             |
| `rt_hash_opt_byte`   | `(opt: byte?) -> int`             |
| `rt_hash_opt_int`    | `(opt: int?) -> int`              |
| `rt_hash_opt_string` | `(opt: string?) -> int`           |
| `rt_hash_ptr`        | `(ptr: void*) -> int`             |
| `rt_hash_opt_ptr`    | `(opt: void*?) -> int`            |
