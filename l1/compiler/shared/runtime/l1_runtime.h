#ifndef L1_RUNTIME_H
#define L1_RUNTIME_H

/*
 * SPDX-License-Identifier: MIT OR Apache-2.0
 * Copyright (c) 2025-2026 gwz
 */

/**
 * @file l1_runtime.h
 * L1 Runtime Library (bootstrap runtime copy)
 *
 * Header-only C99 runtime providing:
 * - Memory allocation and deallocation
 * - Whole-file I/O operations
 * - Basic printing to stdout/stderr
 * - Panic mechanism for defined runtime aborts
 * - UB-free integer operations
 * - String type and operations
 * - Optional type support
 * - Random number generation
 * - Wall/monotonic time snapshots and local-time metadata
 * - Support for Dea `new` and `drop` semantics
 * - Environment variable access
 * - Reading from stdin
 * - Errno access
 *
 * Design principles:
 * - All UB and platform quirks are confined to this file
 * - Dea programs use dea_int (int32_t); this layer handles size_t conversion
 * - Portable C99 code, no compiler-specific extensions
 */

#include <stdio.h>
#include <stdlib.h>
#include <stdint.h>
#include <inttypes.h>
#include <stddef.h>
#include <string.h>
#include <stdarg.h>
#include <errno.h>
#include <time.h>
#include <sys/types.h>
#include <sys/stat.h>

#if defined(_WIN32)
#include <process.h>
#else
#include <unistd.h>
#include <sys/wait.h>
#endif

#include "l0_siphash.h"

/* =========================================================================
 * Compiler-specific builtins and attributes
 * ========================================================================= */

#if defined(__TINYC__) && __TINYC__ >= 928
/* __builtin_unreachable added in mob branch post-0.9.27 */
#   define DEA_UNREACHABLE(_s) __builtin_unreachable()
#elif defined(__GNUC__) || defined(__clang__)
#   define DEA_UNREACHABLE(_s) __builtin_unreachable()
#else
#   define DEA_UNREACHABLE(_s) rt_panic(_s)
#endif

/* =========================================================================
 * Optional tracing support (compile-time toggles)
 * ========================================================================= */

#ifdef DEA_TRACE_ARC
/**
 * Trace reference counting operations to stderr.
 */
#define _RT_TRACE_ARC(...) \
    do { \
        fprintf(stderr, "[l0][arc] "); \
        fprintf(stderr, __VA_ARGS__); \
        fprintf(stderr, "\n"); \
        fflush(stderr); \
    } while (0)
/**
 * Trace reference counting operations with location info.
 */
#define _RT_TRACE_ARC_LOC(loc_file, loc_line, ...) \
    do { \
        fprintf(stderr, "[l0][arc] "); \
        fprintf(stderr, __VA_ARGS__); \
        fprintf(stderr, " loc=\"%s\":%d", loc_file, loc_line); \
        fprintf(stderr, "\n"); \
        fflush(stderr); \
    } while (0)
#else
#define _RT_TRACE_ARC(...) ((void)0)
#define _RT_TRACE_ARC_LOC(loc_file, loc_line, ...) ((void)0)
#endif

#ifdef DEA_TRACE_MEMORY
/**
 * Trace memory allocation operations to stderr.
 */
#define _RT_TRACE_MEM(...) \
    do { \
        fprintf(stderr, "[l0][mem] "); \
        fprintf(stderr, __VA_ARGS__); \
        fprintf(stderr, "\n"); \
        fflush(stderr); \
    } while (0)
/**
 * Trace memory allocation operations with location info.
 */
#define _RT_TRACE_MEM_LOC(loc_file, loc_line, ...) \
    do { \
        fprintf(stderr, "[l0][mem] "); \
        fprintf(stderr, __VA_ARGS__); \
        fprintf(stderr, " loc=\"%s\":%d", loc_file, loc_line); \
        fprintf(stderr, "\n"); \
        fflush(stderr); \
    } while (0)
#else
#define _RT_TRACE_MEM(...) ((void)0)
#define _RT_TRACE_MEM_LOC(loc_file, loc_line, ...) ((void)0)
#endif

/* =========================================================================
 * Core type definitions
 * ========================================================================= */

typedef uint8_t  dea_bool;

typedef int8_t   dea_tiny;
typedef int16_t  dea_short;
typedef int32_t  dea_int;
typedef int64_t  dea_long;

typedef uint8_t  dea_byte;
typedef uint16_t dea_ushort;
typedef uint32_t dea_uint;
typedef uint64_t dea_ulong;

typedef float    dea_float;
typedef double   dea_double;

/**
 * @struct _dea_h_string
 * Heap-allocated L0 string header.
 *
 * L0 string: length-tracked, reference counted, immutable character sequence.
 * Strings are always length-tracked to prevent out-of-bounds access.
 * A dea_string with len=0 represents an empty string.
 * Data should be NULL for empty strings to maintain consistency, but non-NULL is tolerated.
 * refcount is used for memory management; if refcount == INT32_MAX, the string
 * is not reference counted (e.g. allocated strings).
 * Strings with refcount > 0 are reference counted and should be freed when refcount reaches zero.
 * Strings with refcount == INT32_MAX are not ref-counted, but heap-allocated or empty, and should be freed manually.
 * Strings with refcount == _RT_MEM_SENTINEL have already been freed (double-free detected).
 * Data is null-terminated for C interoperability, but length is authoritative.
 */
typedef struct {
    dea_int refcount;    /**< Reference count for memory management, or INT32_MAX if not reference counted */
    dea_int len;         /**< Length in bytes (must be >= 0) */
    char bytes[];        /**< Mutable character data, 0-terminated for C interoperability */
} _dea_h_string;

#define DEA_STRING_K_STATIC  0
#define DEA_STRING_K_HEAP    1

/**
 * Sentinel value for memory checks.
 */
static const dea_int _RT_MEM_SENTINEL = 0xF00DB10C;

/**
 * @struct dea_string
 * Unified L0 string type (static or heap-allocated).
 */
typedef struct {
    unsigned int kind : 1;      /**< Kind of string: either DEA_STRING_K_STATIC (0) or DEA_STRING_K_HEAP (1) */
    unsigned int : 0;           /**< Align to next unsigned int boundary */
    union {
        struct {
            dea_int len;         /**< Length in bytes (for constant inline strings) */
            const char* bytes;  /**< Pointer to character data (may be NULL for empty string) */
        } s_str;                /**< Static string structure for constant inline strings */
        _dea_h_string *h_str;    /**< Heap-allocated string structure for dynamic strings */
    } data;
} dea_string;

/**
 * Static empty string instance.
 */
static dea_string DEA_STRING_EMPTY = { 0, { .s_str = { 0, NULL } } };

/**
 * String literal construction macro.
 */
#define DEA_STRING_CONST(str_data, str_len) { .kind = DEA_STRING_K_STATIC, .data.s_str = { .len = (str_len), .bytes = (str_data) } }

/* =========================================================================
 * Optional type wrappers (T? as {has_value, value})
 * ========================================================================= */

#ifndef DEA_OPT_BOOL_DEFINED
#define DEA_OPT_BOOL_DEFINED
/** @struct dea_opt_bool Optional boolean wrapper. */
typedef struct { dea_bool has_value; dea_bool value; } dea_opt_bool;
#endif /* DEA_OPT_BOOL_DEFINED */

#ifndef DEA_OPT_TINY_DEFINED
#define DEA_OPT_TINY_DEFINED
/** @struct dea_opt_tiny Optional tiny wrapper. */
typedef struct { dea_bool has_value; dea_tiny value; } dea_opt_tiny;
#endif /* DEA_OPT_TINY_DEFINED */

#ifndef DEA_OPT_BYTE_DEFINED
#define DEA_OPT_BYTE_DEFINED
/** @struct dea_opt_byte Optional byte wrapper. */
typedef struct { dea_bool has_value; dea_byte value; } dea_opt_byte;
#endif /* DEA_OPT_BYTE_DEFINED */

#ifndef DEA_OPT_SHORT_DEFINED
#define DEA_OPT_SHORT_DEFINED
/** @struct dea_opt_short Optional short wrapper. */
typedef struct { dea_bool has_value; dea_short value; } dea_opt_short;
#endif /* DEA_OPT_SHORT_DEFINED */

#ifndef DEA_OPT_INT_DEFINED
#define DEA_OPT_INT_DEFINED
/** @struct dea_opt_int Optional integer wrapper. */
typedef struct { dea_bool has_value; dea_int value; } dea_opt_int;
#endif /* DEA_OPT_INT_DEFINED */

#ifndef DEA_OPT_USHORT_DEFINED
#define DEA_OPT_USHORT_DEFINED
/** @struct dea_opt_ushort Optional ushort wrapper. */
typedef struct { dea_bool has_value; dea_ushort value; } dea_opt_ushort;
#endif /* DEA_OPT_USHORT_DEFINED */

#ifndef DEA_OPT_UINT_DEFINED
#define DEA_OPT_UINT_DEFINED
/** @struct dea_opt_uint Optional uint wrapper. */
typedef struct { dea_bool has_value; dea_uint value; } dea_opt_uint;
#endif /* DEA_OPT_UINT_DEFINED */

#ifndef DEA_OPT_LONG_DEFINED
#define DEA_OPT_LONG_DEFINED
/** @struct dea_opt_long Optional long wrapper. */
typedef struct { dea_bool has_value; dea_long value; } dea_opt_long;
#endif /* DEA_OPT_LONG_DEFINED */

#ifndef DEA_OPT_ULONG_DEFINED
#define DEA_OPT_ULONG_DEFINED
/** @struct dea_opt_ulong Optional ulong wrapper. */
typedef struct { dea_bool has_value; dea_ulong value; } dea_opt_ulong;
#endif /* DEA_OPT_ULONG_DEFINED */

#ifndef DEA_OPT_STRING_DEFINED
#define DEA_OPT_STRING_DEFINED
/** @struct dea_opt_string Optional string wrapper. */
typedef struct { dea_bool has_value; dea_string value; } dea_opt_string;
#endif /* DEA_OPT_STRING_DEFINED */

/** @struct _dea_base_opt Base structure for optional types to access has_value. */
typedef struct { dea_bool has_value; } _dea_base_opt;

/** Static instance for null optional string. */
static dea_opt_string DEA_OPT_STRING_NULL = { .has_value = 0, .value = { 0 } };
/** Static instance for empty optional string. */
static dea_opt_string DEA_OPT_STRING_EMPTY = { .has_value = 1, .value = { 0 } };

/**
 * @struct dea_sys_rt_RtTimeParts
 * Definition for `sys.rt::RtTimeParts`.
 */
#ifndef DEA_DEFINED_dea_sys_rt_RtTimeParts
#define DEA_DEFINED_dea_sys_rt_RtTimeParts
struct dea_sys_rt_RtTimeParts {
    dea_int sec;
    dea_int nsec;
};
#endif

/**
 * @struct dea_sys_rt_RtFileInfo
 * Definition for `sys.rt::RtFileInfo`.
 */
#ifndef DEA_DEFINED_dea_sys_rt_RtFileInfo
#define DEA_DEFINED_dea_sys_rt_RtFileInfo
struct dea_sys_rt_RtFileInfo {
    dea_bool exists;
    dea_bool is_file;
    dea_bool is_dir;
    dea_opt_int size;
    dea_opt_int mtime_sec;
    dea_opt_int mtime_nsec;
};
#endif

/* =========================================================================
 * Argument handling
 * ========================================================================= */

static int _rt_argc = 0;
static char** _rt_argv = NULL;

/**
 * Initialize command-line arguments.
 *
 * @param argc Number of arguments.
 * @param argv Argument vector.
 */
void _rt_init_args(int argc, char** argv) {
    _rt_argc = argc;
    _rt_argv = argv;
}

/* =========================================================================
 * Panic mechanism
 * ========================================================================= */

/**
 * Abort the program with a message.
 *
 * @param message The panic message.
 */
static void _rt_panic(const char* message) {
    if (message == NULL) {
        message = "Guru Meditation";
    }
    fflush(stdout);
    fprintf(stderr, "Software Failure: %s\n", message);
    fflush(stderr);
    abort();
}

/**
 * Abort the program with a formatted message.
 *
 * @param fmt Format string.
 */
static void _rt_panic_fmt(const char* fmt, ...) {
    va_list args;
    fflush(stdout);
    fprintf(stderr, "Software Failure: ");
    va_start(args, fmt);
    vfprintf(stderr, fmt, args);
    va_end(args);
    fprintf(stderr, "\n");
    fflush(stderr);
    abort();
}

/* =========================================================================
 * UB-free integer helpers
 * ========================================================================= */

/**
 * Safe integer division.
 *
 * @param a Dividend.
 * @param b Divisor.
 * @return Quotient.
 */
static dea_int _rt_idiv(dea_int a, dea_int b) {
    if (b == 0) {
        _rt_panic("division by zero");
    }
    if (a == INT32_MIN && b == -1) {
        _rt_panic("division overflow: INT32_MIN / -1");
    }
    return a / b;
}

/**
 * Safe integer modulo.
 *
 * @param a Dividend.
 * @param b Divisor.
 * @return Remainder.
 */
static dea_int _rt_imod(dea_int a, dea_int b) {
    if (b == 0) {
        _rt_panic("modulo by zero");
    }
    if (a == INT32_MIN && b == -1) {
        _rt_panic("modulo overflow: INT32_MIN % -1");
    }
    return a % b;
}

/**
 * Safe integer addition with overflow check.
 *
 * @param a First operand.
 * @param b Second operand.
 * @return Sum.
 */
static dea_int _rt_iadd(dea_int a, dea_int b) {
    if ((b > 0 && a > INT32_MAX - b) || (b < 0 && a < INT32_MIN - b)) {
        _rt_panic("integer addition overflow");
    }
    return a + b;
}

/**
 * Safe integer subtraction with overflow check.
 *
 * @param a First operand.
 * @param b Second operand.
 * @return Difference.
 */
static dea_int _rt_isub(dea_int a, dea_int b) {
    if ((b < 0 && a > INT32_MAX + b) || (b > 0 && a < INT32_MIN + b)) {
        _rt_panic("integer subtraction overflow");
    }
    return a - b;
}

/**
 * Safe integer multiplication with overflow check.
 *
 * @param a First operand.
 * @param b Second operand.
 * @return Product.
 */
static dea_int _rt_imul(dea_int a, dea_int b) {
    /* Zero multiplication always succeeds */
    if (a == 0 || b == 0) {
        return 0;
    }

    /* Special case: -1 * INT32_MIN or INT32_MIN * -1 = 2147483648, which overflows int32_t */
    if ((a == -1 && b == INT32_MIN) || (b == -1 && a == INT32_MIN)) {
        _rt_panic("integer multiplication overflow");
    }

    /* Both operands positive: overflow if a > INT32_MAX / b */
    if (a > 0 && b > 0) {
        if (a > INT32_MAX / b) {
            _rt_panic("integer multiplication overflow");
        }
    }
    /* Both operands negative: result is positive, overflow if a < INT32_MAX / b
     * Note: We already handled the a=-1,b=INT32_MIN case above, so b != INT32_MIN here
     * and INT32_MAX / b is safe */
    else if (a < 0 && b < 0) {
        if (a < INT32_MAX / b) {
            _rt_panic("integer multiplication overflow");
        }
    }
    /* Mixed signs: result is negative or zero */
    else {
        /* We already handled the special cases where b=-1,a=INT32_MIN or a=-1,b=INT32_MIN
         * So all divisions below are safe from overflow */
        if (a > 0) {
            /* a > 0, b < 0: underflow if a > INT32_MIN / b
             * Since b != -1 (handled above), INT32_MIN / b is safe */
            if (b != -1 && a > INT32_MIN / b) {
                _rt_panic("integer multiplication overflow");
            }
        } else {
            /* a < 0, b > 0: underflow if a < INT32_MIN / b */
            if (a < INT32_MIN / b) {
                _rt_panic("integer multiplication overflow");
            }
        }
    }

    return a * b;
}

/** Narrow dea_int to dea_tiny with range check. */
dea_tiny _rt_narrow_dea_tiny(dea_int value) {
    if (value < -128 || value > 127) {
        _rt_panic("integer to tiny cast overflow");
    }
    return (dea_tiny)value;
}

/** Narrow dea_int to dea_byte with range check. */
dea_byte _rt_narrow_dea_byte(dea_int value) {
    if (value < 0 || value > 255) {
        _rt_panic("integer to byte cast overflow");
    }
    return (dea_byte)value;
}

/** Narrow dea_int to dea_short with range check. */
dea_short _rt_narrow_dea_short(dea_int value) {
    if (value < -32768 || value > 32767) {
        _rt_panic("integer to short cast overflow");
    }
    return (dea_short)value;
}

/** Narrow dea_int to dea_ushort with range check. */
dea_ushort _rt_narrow_dea_ushort(dea_int value) {
    if (value < 0 || value > 65535) {
        _rt_panic("integer to ushort cast overflow");
    }
    return (dea_ushort)value;
}

/** Narrow dea_int to dea_uint with range check. */
dea_uint _rt_narrow_dea_uint(dea_int value) {
    if (value < 0) {
        _rt_panic("integer to uint cast overflow");
    }
    return (dea_uint)value;
}

/** Narrow dea_int to dea_ulong with range check. */
dea_ulong _rt_narrow_dea_ulong(dea_int value) {
    if (value < 0) {
        _rt_panic("integer to ulong cast overflow");
    }
    return (dea_ulong)value;
}

/**
 * Safe unsigned integer division.
 *
 * @param a Dividend.
 * @param b Divisor.
 * @return Quotient.
 */
static dea_uint _rt_udiv(dea_uint a, dea_uint b) {
    if (b == 0) {
        _rt_panic("division by zero");
    }
    return a / b;
}

/**
 * Safe unsigned integer modulo.
 *
 * @param a Dividend.
 * @param b Divisor.
 * @return Remainder.
 */
static dea_uint _rt_umod(dea_uint a, dea_uint b) {
    if (b == 0) {
        _rt_panic("modulo by zero");
    }
    return a % b;
}

/** Safe unsigned integer addition with overflow check. */
static dea_uint _rt_uadd(dea_uint a, dea_uint b) {
    if (UINT32_MAX - a < b) {
        _rt_panic("uint addition overflow");
    }
    return a + b;
}

/** Safe unsigned integer subtraction with underflow check. */
static dea_uint _rt_usub(dea_uint a, dea_uint b) {
    if (a < b) {
        _rt_panic("uint subtraction underflow");
    }
    return a - b;
}

/** Safe unsigned integer multiplication with overflow check. */
static dea_uint _rt_umul(dea_uint a, dea_uint b) {
    if (a == 0 || b == 0) {
        return 0;
    }
    if (a > UINT32_MAX / b) {
        _rt_panic("uint multiplication overflow");
    }
    return a * b;
}

/** Safe 64-bit signed integer division. */
static dea_long _rt_ldiv(dea_long a, dea_long b) {
    if (b == 0) {
        _rt_panic("division by zero");
    }
    if (a == INT64_MIN && b == -1) {
        _rt_panic("division overflow: INT64_MIN / -1");
    }
    return a / b;
}

/** Safe 64-bit signed integer modulo. */
static dea_long _rt_lmod(dea_long a, dea_long b) {
    if (b == 0) {
        _rt_panic("modulo by zero");
    }
    if (a == INT64_MIN && b == -1) {
        _rt_panic("modulo overflow: INT64_MIN % -1");
    }
    return a % b;
}

/** Safe 64-bit signed integer addition with overflow check. */
static dea_long _rt_ladd(dea_long a, dea_long b) {
    if ((b > 0 && a > INT64_MAX - b) || (b < 0 && a < INT64_MIN - b)) {
        _rt_panic("long addition overflow");
    }
    return a + b;
}

/** Safe 64-bit signed integer subtraction with overflow check. */
static dea_long _rt_lsub(dea_long a, dea_long b) {
    if ((b < 0 && a > INT64_MAX + b) || (b > 0 && a < INT64_MIN + b)) {
        _rt_panic("long subtraction overflow");
    }
    return a - b;
}

/** Safe 64-bit signed integer multiplication with overflow check. */
static dea_long _rt_lmul(dea_long a, dea_long b) {
    if (a == 0 || b == 0) {
        return 0;
    }
    if ((a == -1 && b == INT64_MIN) || (b == -1 && a == INT64_MIN)) {
        _rt_panic("long multiplication overflow");
    }
    if (a > 0 && b > 0) {
        if (a > INT64_MAX / b) {
            _rt_panic("long multiplication overflow");
        }
    } else if (a < 0 && b < 0) {
        if (a < INT64_MAX / b) {
            _rt_panic("long multiplication overflow");
        }
    } else {
        if (a > 0) {
            if (b != -1 && a > INT64_MIN / b) {
                _rt_panic("long multiplication overflow");
            }
        } else {
            if (a < INT64_MIN / b) {
                _rt_panic("long multiplication overflow");
            }
        }
    }
    return a * b;
}

/** Safe 64-bit unsigned integer division. */
static dea_ulong _rt_uldiv(dea_ulong a, dea_ulong b) {
    if (b == 0) {
        _rt_panic("division by zero");
    }
    return a / b;
}

/** Safe 64-bit unsigned integer modulo. */
static dea_ulong _rt_ulmod(dea_ulong a, dea_ulong b) {
    if (b == 0) {
        _rt_panic("modulo by zero");
    }
    return a % b;
}

/** Safe 64-bit unsigned integer addition with overflow check. */
static dea_ulong _rt_uladd(dea_ulong a, dea_ulong b) {
    if (UINT64_MAX - a < b) {
        _rt_panic("ulong addition overflow");
    }
    return a + b;
}

/** Safe 64-bit unsigned integer subtraction with underflow check. */
static dea_ulong _rt_ulsub(dea_ulong a, dea_ulong b) {
    if (a < b) {
        _rt_panic("ulong subtraction underflow");
    }
    return a - b;
}

/** Safe 64-bit unsigned integer multiplication with overflow check. */
static dea_ulong _rt_ulmul(dea_ulong a, dea_ulong b) {
    if (a == 0 || b == 0) {
        return 0;
    }
    if (a > UINT64_MAX / b) {
        _rt_panic("ulong multiplication overflow");
    }
    return a * b;
}

/** Checked cast from signed 64-bit to dea_tiny. */
static dea_tiny _rt_cast_dea_tiny_from_signed(dea_long value) {
    if (value < INT8_MIN || value > INT8_MAX) {
        _rt_panic("integer to tiny cast overflow");
    }
    return (dea_tiny)value;
}

/** Checked cast from unsigned 64-bit to dea_tiny. */
static dea_tiny _rt_cast_dea_tiny_from_unsigned(dea_ulong value) {
    if (value > (dea_ulong)INT8_MAX) {
        _rt_panic("integer to tiny cast overflow");
    }
    return (dea_tiny)value;
}

/** Checked cast from signed 64-bit to dea_byte. */
static dea_byte _rt_cast_dea_byte_from_signed(dea_long value) {
    if (value < 0 || value > UINT8_MAX) {
        _rt_panic("integer to byte cast overflow");
    }
    return (dea_byte)value;
}

/** Checked cast from unsigned 64-bit to dea_byte. */
static dea_byte _rt_cast_dea_byte_from_unsigned(dea_ulong value) {
    if (value > UINT8_MAX) {
        _rt_panic("integer to byte cast overflow");
    }
    return (dea_byte)value;
}

/** Checked cast from signed 64-bit to dea_short. */
static dea_short _rt_cast_dea_short_from_signed(dea_long value) {
    if (value < INT16_MIN || value > INT16_MAX) {
        _rt_panic("integer to short cast overflow");
    }
    return (dea_short)value;
}

/** Checked cast from unsigned 64-bit to dea_short. */
static dea_short _rt_cast_dea_short_from_unsigned(dea_ulong value) {
    if (value > (dea_ulong)INT16_MAX) {
        _rt_panic("integer to short cast overflow");
    }
    return (dea_short)value;
}

/** Checked cast from signed 64-bit to dea_ushort. */
static dea_ushort _rt_cast_dea_ushort_from_signed(dea_long value) {
    if (value < 0 || value > UINT16_MAX) {
        _rt_panic("integer to ushort cast overflow");
    }
    return (dea_ushort)value;
}

/** Checked cast from unsigned 64-bit to dea_ushort. */
static dea_ushort _rt_cast_dea_ushort_from_unsigned(dea_ulong value) {
    if (value > UINT16_MAX) {
        _rt_panic("integer to ushort cast overflow");
    }
    return (dea_ushort)value;
}

/** Checked cast from signed 64-bit to dea_int. */
static dea_int _rt_cast_dea_int_from_signed(dea_long value) {
    if (value < INT32_MIN || value > INT32_MAX) {
        _rt_panic("integer to int cast overflow");
    }
    return (dea_int)value;
}

/** Checked cast from unsigned 64-bit to dea_int. */
static dea_int _rt_cast_dea_int_from_unsigned(dea_ulong value) {
    if (value > (dea_ulong)INT32_MAX) {
        _rt_panic("integer to int cast overflow");
    }
    return (dea_int)value;
}

/** Checked cast from signed 64-bit to dea_uint. */
static dea_uint _rt_cast_dea_uint_from_signed(dea_long value) {
    if (value < 0 || value > UINT32_MAX) {
        _rt_panic("integer to uint cast overflow");
    }
    return (dea_uint)value;
}

/** Checked cast from unsigned 64-bit to dea_uint. */
static dea_uint _rt_cast_dea_uint_from_unsigned(dea_ulong value) {
    if (value > UINT32_MAX) {
        _rt_panic("integer to uint cast overflow");
    }
    return (dea_uint)value;
}

/** Checked cast from signed 64-bit to dea_long. */
static dea_long _rt_cast_dea_long_from_signed(dea_long value) {
    return value;
}

/** Checked cast from unsigned 64-bit to dea_long. */
static dea_long _rt_cast_dea_long_from_unsigned(dea_ulong value) {
    if (value > (dea_ulong)INT64_MAX) {
        _rt_panic("integer to long cast overflow");
    }
    return (dea_long)value;
}

/** Checked cast from signed 64-bit to dea_ulong. */
static dea_ulong _rt_cast_dea_ulong_from_signed(dea_long value) {
    if (value < 0) {
        _rt_panic("integer to ulong cast overflow");
    }
    return (dea_ulong)value;
}

/** Checked cast from unsigned 64-bit to dea_ulong. */
static dea_ulong _rt_cast_dea_ulong_from_unsigned(dea_ulong value) {
    return value;
}

/* =========================================================================
 * UB-free optional type helpers
 * ========================================================================= */

/**
 * Unwrap a pointer, panicking if NULL.
 *
 * @param opt Pointer to unwrap.
 * @param type_name Name of the type for error reporting.
 * @return Unwrapped pointer.
 */
static inline void *_unwrap_ptr(void *opt, const char *type_name) {
    if (opt == NULL) {
        _rt_panic_fmt("unwrap of empty optional: '%s'", type_name);
    }
    return opt;
}

/**
 * Unwrap an optional type structure, panicking if it has no value.
 *
 * @param opt_ptr Pointer to the optional structure.
 * @param type_name Name of the type for error reporting.
 * @return Pointer to the optional structure.
 */
static inline void *_unwrap_opt(void *opt_ptr, const char *type_name) {
    _dea_base_opt *base = (_dea_base_opt*)opt_ptr;
    if (!base->has_value) {
        _rt_panic_fmt("unwrap of empty optional: '%s'", type_name);
    }
    return opt_ptr;
}

/* =========================================================================
 * String construction and operations
 * ========================================================================= */

/**
 * Create an L0 string from a constant C string.
 * Returns a string with len=0 if c_str is NULL.
 *
 * Note: Does NOT allocate or copy - just wraps the existing C string.
 * Use only for string literals or static const data.
 *
 * @param c_str Constant C string.
 * @return L0 string.
 */
static dea_string _rt_dea_string_from_const_literal(const char *c_str) {
    dea_string s;
    if (c_str == NULL) {
        return DEA_STRING_EMPTY;
    } else {
        size_t len = strlen(c_str);
        if (len > INT32_MAX) {
            _rt_panic("_rt_dea_string_from_const_literal: string too long for dea_int");
        }
        s.kind = DEA_STRING_K_STATIC;
        s.data.s_str.len = (dea_int)len;
        s.data.s_str.bytes = c_str;
    }
    return s;
}

/**
 * Initialize a heap-allocated DEA_string in the given memory.
 * Character data (bytes[]) is uninitialized; caller must fill it in.
 * Length is assumed to be already validated by the caller.
 * Size of mem MUST be at least sizeof(_dea_h_string) + s_len + 1.
 *
 * The returned string is of kind DEA_STRING_K_HEAP and
 * its data is null-terminated in advance.
 *
 * @param mem Allocated memory block.
 * @param s_len Length of the string.
 * @return Initialized L0 string.
 */
static dea_string _rt_init_heap_string(void *mem, dea_int s_len) {
    dea_string s;
    _dea_h_string *hs = (_dea_h_string *)mem;
    hs->refcount = 1;       /* reference counted */
    hs->len = (dea_int)s_len;
    hs->bytes[s_len] = '\0';   /* null-terminate */

    s.kind = DEA_STRING_K_HEAP;
    s.data.h_str = hs;
    return s;
}

/**
 * Allocate a new reference counted DEA_string of the given length.
 * Character data (bytes[]) is uninitialized; caller must fill it in.
 * Panics on allocation failure or negative length.
 * Size of allocated memory is: string header + len + 1 for null terminator.
 *
 * The returned string is of kind DEA_STRING_K_HEAP and
 * its data is null-terminated in advance.
 *
 * @param len Length of the string.
 * @return Allocated L0 string.
 */
#ifdef DEA_TRACE_MEMORY
static dea_string _rt_alloc_string_impl(dea_int len, const char *_loc_file, int _loc_line) {
    if (len < 0) {
        _rt_panic("_rt_alloc_string: negative length");
    }
    void *mem = malloc(sizeof(_dea_h_string) + len + 1);
    if (mem == NULL) {
        _rt_panic("_rt_alloc_string: out of memory");
    }
    dea_string s = _rt_init_heap_string(mem, len);
    _RT_TRACE_MEM_LOC(_loc_file, _loc_line, "op=alloc_string len=%d ptr=%p", (int)len, (void*)s.data.h_str);
    return s;
}
#define _rt_alloc_string(len) _rt_alloc_string_impl((len), __FILE__, __LINE__)
#else
static dea_string _rt_alloc_string(dea_int len) {
    if (len < 0) {
        _rt_panic("_rt_alloc_string: negative length");
    }
    void *mem = malloc(sizeof(_dea_h_string) + len + 1);
    if (mem == NULL) {
        _rt_panic("_rt_alloc_string: out of memory");
    }
    dea_string s = _rt_init_heap_string(mem, len);
    _RT_TRACE_MEM("op=alloc_string len=%d ptr=%p", (int)len, (void*)s.data.h_str);
    return s;
}
#endif

/**
 * Free a string's allocated data, if applicable.
 * If reference counted, decrements reference count and frees when it reaches zero.
 * 
 * @param str L0 string to free.
 */
#if defined(DEA_TRACE_ARC) || defined(DEA_TRACE_MEMORY)
static void _rt_free_string_impl(dea_string str, const char *_loc_file, int _loc_line) {
    if (str.kind == DEA_STRING_K_STATIC) {
        /* Static string: do nothing */
        _RT_TRACE_ARC_LOC(_loc_file, _loc_line, "op=release kind=static ptr=%p rc_before=-1 rc_after=-1 action=noop", (void*)str.data.s_str.bytes);
        return;
    }
    _dea_h_string *hs = str.data.h_str;
    if (hs == NULL) {
        _RT_TRACE_ARC_LOC(_loc_file, _loc_line, "op=release kind=heap ptr=%p rc_before=-1 rc_after=-1 action=panic-null-ptr", (void*)hs);
        _RT_TRACE_MEM_LOC(_loc_file, _loc_line, "op=free_string ptr=%p action=panic-null-ptr", (void*)hs);
        _rt_panic("_rt_free_string: null heap string pointer");
    }
    dea_int rc_before = hs->refcount;
    if (rc_before > 0 && rc_before < INT32_MAX) {
        /* Reference counted string */
        hs->refcount--;
        if (hs->refcount == 0) {
            _RT_TRACE_ARC_LOC(
                _loc_file, _loc_line,
                "op=release kind=heap ptr=%p rc_before=%d rc_after=0 action=free",
                (void*)hs, (int)rc_before
            );
            _RT_TRACE_MEM_LOC(_loc_file, _loc_line, "op=free_string ptr=%p action=free", (void*)hs);
            hs->refcount = _RT_MEM_SENTINEL; /* prevent double free */
            free((void*)hs);
        } else {
            _RT_TRACE_ARC_LOC(
                _loc_file, _loc_line,
                "op=release kind=heap ptr=%p rc_before=%d rc_after=%d action=keep",
                (void*)hs, (int)rc_before, (int)hs->refcount
            );
            _RT_TRACE_MEM_LOC(_loc_file, _loc_line, "op=free_string ptr=%p action=decrement-only", (void*)hs);
        }
        return;
    }
    if (rc_before == INT32_MAX) {
        /* Non-reference counted string: do nothing */
        _RT_TRACE_ARC_LOC(
            _loc_file, _loc_line,
            "op=release kind=heap ptr=%p rc_before=%d rc_after=%d action=noop-nonref",
            (void*)hs, (int)rc_before, (int)rc_before
        );
        _RT_TRACE_MEM_LOC(_loc_file, _loc_line, "op=free_string ptr=%p action=noop-nonref", (void*)hs);
        return;
    }
    if (rc_before == _RT_MEM_SENTINEL) {
        _RT_TRACE_ARC_LOC(
            _loc_file, _loc_line,
            "op=release kind=heap ptr=%p rc_before=%d rc_after=%d action=panic-double-free",
            (void*)hs, (int)rc_before, (int)rc_before
        );
        _RT_TRACE_MEM_LOC(_loc_file, _loc_line, "op=free_string ptr=%p action=panic-double-free", (void*)hs);
        _rt_panic("_rt_free_string: double free detected");
    }
    _RT_TRACE_ARC_LOC(
        _loc_file, _loc_line,
        "op=release kind=heap ptr=%p rc_before=%d rc_after=%d action=panic-invalid-state",
        (void*)hs, (int)rc_before, (int)rc_before
    );
    _RT_TRACE_MEM_LOC(_loc_file, _loc_line, "op=free_string ptr=%p action=panic-invalid-state", (void*)hs);
    _rt_panic_fmt("_rt_free_string: invalid string refcount state: %d", (int)hs->refcount);
}
#define _rt_free_string(str) _rt_free_string_impl((str), __FILE__, __LINE__)
#else
static void _rt_free_string(dea_string str) {
    if (str.kind == DEA_STRING_K_STATIC) {
        /* Static string: do nothing */
        _RT_TRACE_ARC("op=release kind=static ptr=%p rc_before=-1 rc_after=-1 action=noop", (void*)str.data.s_str.bytes);
        return;
    }
    _dea_h_string *hs = str.data.h_str;
    if (hs == NULL) {
        _RT_TRACE_ARC("op=release kind=heap ptr=%p rc_before=-1 rc_after=-1 action=panic-null-ptr", (void*)hs);
        _RT_TRACE_MEM("op=free_string ptr=%p action=panic-null-ptr", (void*)hs);
        _rt_panic("_rt_free_string: null heap string pointer");
    }
    dea_int rc_before = hs->refcount;
    if (rc_before > 0 && rc_before < INT32_MAX) {
        /* Reference counted string */
        hs->refcount--;
        if (hs->refcount == 0) {
            _RT_TRACE_ARC(
                "op=release kind=heap ptr=%p rc_before=%d rc_after=0 action=free",
                (void*)hs, (int)rc_before
            );
            _RT_TRACE_MEM("op=free_string ptr=%p action=free", (void*)hs);
            hs->refcount = _RT_MEM_SENTINEL; /* prevent double free */
            free((void*)hs);
        } else {
            _RT_TRACE_ARC(
                "op=release kind=heap ptr=%p rc_before=%d rc_after=%d action=keep",
                (void*)hs, (int)rc_before, (int)hs->refcount
            );
            _RT_TRACE_MEM("op=free_string ptr=%p action=decrement-only", (void*)hs);
        }
        return;
    }
    if (rc_before == INT32_MAX) {
        /* Non-reference counted string: do nothing */
        _RT_TRACE_ARC(
            "op=release kind=heap ptr=%p rc_before=%d rc_after=%d action=noop-nonref",
            (void*)hs, (int)rc_before, (int)rc_before
        );
        _RT_TRACE_MEM("op=free_string ptr=%p action=noop-nonref", (void*)hs);
        return;
    }
    if (rc_before == _RT_MEM_SENTINEL) {
        _RT_TRACE_ARC(
            "op=release kind=heap ptr=%p rc_before=%d rc_after=%d action=panic-double-free",
            (void*)hs, (int)rc_before, (int)rc_before
        );
        _RT_TRACE_MEM("op=free_string ptr=%p action=panic-double-free", (void*)hs);
        _rt_panic("_rt_free_string: double free detected");
    }
    _RT_TRACE_ARC(
        "op=release kind=heap ptr=%p rc_before=%d rc_after=%d action=panic-invalid-state",
        (void*)hs, (int)rc_before, (int)rc_before
    );
    _RT_TRACE_MEM("op=free_string ptr=%p action=panic-invalid-state", (void*)hs);
    _rt_panic_fmt("_rt_free_string: invalid string refcount state: %d", (int)hs->refcount);
}
#endif

/**
 * Reallocate a heap string to a new length.
 * 
 * @param s Current L0 string.
 * @param new_len New length.
 * @return Updated L0 string.
 */
static dea_string _rt_realloc_string(dea_string s, dea_int new_len) {
    if (new_len < 0) {
        _rt_panic("_rt_realloc_string: negative length");
    }
    if (new_len == 0) {
        _rt_free_string(s);
        return DEA_STRING_EMPTY;
    }
    if (s.kind == DEA_STRING_K_STATIC && s.data.s_str.len == 0) {
        /* Reallocating empty static string: allocate new heap string */
        return _rt_alloc_string(new_len);
    }
    if (s.kind != DEA_STRING_K_HEAP || s.data.h_str == NULL) {
        _RT_TRACE_MEM("op=realloc_string old_ptr=%p new_len=%d action=panic-invalid-string", (void*)s.data.h_str, (int)new_len);
        _rt_panic("_rt_realloc_string: string is not heap-allocated");
    }
    
    /* Use volatile to prevent the compiler from tracking the pointer across realloc 
       and complaining about use-after-free when tracing the old pointer value. */
    volatile uintptr_t old_ptr_addr = (uintptr_t)s.data.h_str;
    size_t new_size = sizeof(_dea_h_string) + new_len + 1;
    void *new_mem = realloc((void*)old_ptr_addr, new_size);
    if (new_mem == NULL) {
        _RT_TRACE_MEM("op=realloc_string old_ptr=%p new_len=%d action=panic-oom", (void*)old_ptr_addr, (int)new_len);
        _rt_panic("_rt_realloc_string: out of memory");
    }
    _dea_h_string *new_hs = (_dea_h_string *)new_mem;
    new_hs->len = new_len;
    new_hs->bytes[new_len] = '\0'; /* null-terminate */
    s.data.h_str = new_hs;
    _RT_TRACE_MEM(
        "op=realloc_string old_ptr=%p new_ptr=%p new_len=%d action=ok",
        (void*)old_ptr_addr, (void*)new_hs, (int)new_len
    );
    return s;
}

/**
 * Create a new reference counted DEA_string from a null-terminated C string.
 * Allocates new memory and copies data.
 * 
 * @param c_str Null-terminated C string.
 * @return L0 string.
 */
static dea_string _rt_new_dea_string(const char *c_str) {
    if (c_str == NULL) {
        return DEA_STRING_EMPTY;
    }
    size_t len = strlen(c_str);
    if ((uint64_t)len > INT32_MAX) {
        _rt_panic("_rt_new_dea_string: string too long for dea_int");
    }
    dea_string s = _rt_alloc_string((dea_int)len);
    _dea_h_string *hs = s.data.h_str;
    memcpy(hs->bytes, c_str, len + 1);

    return s;
}

/**
 * Gets the null-terminated C string underlying an L0 string.
 * or NULL if not available, e.g. for static empty strings.
 * Useful when interfacing with C APIs that require null-terminated strings.
 *
 * Note: This is an internal helper, not exposed to L0 code.
 * 
 * @param s L0 string.
 * @return Pointer to character data.
 */
static char *_rt_string_bytes(dea_string s) {
    switch (s.kind) {
        case DEA_STRING_K_STATIC:
            return (char*)s.data.s_str.bytes;
        case DEA_STRING_K_HEAP:
            if (s.data.h_str != NULL) {
                return s.data.h_str->bytes;
            }
            /* fallthrough */
        default:
            _rt_panic_fmt("_rt_string_bytes: invalid string kind: %d or null data", (int)s.kind);
            return NULL; /* Unreachable */
    }
}

/* =========================================================================
 * User string operations
 * ========================================================================= */

/**
 * Get the length of a string.
 * 
 * @param str L0 string.
 * @return Length in bytes.
 *
 * L0 signature: `extern func rt_strlen(str: string) -> int;` 
 */
static dea_int rt_strlen(dea_string str) {
    switch(str.kind) {
    case DEA_STRING_K_STATIC:
        return str.data.s_str.len;
    case DEA_STRING_K_HEAP:
        if (str.data.h_str == NULL) {
            _rt_panic("rt_strlen: string data is null");
            return 0; /* Unreachable */
        }
        return str.data.h_str->len;
    default:
        _rt_panic_fmt("rt_strlen: invalid string kind: %d", (int)str.kind);
        return 0; /* Unreachable */
    }
}

/**
 * Bounds-checked character access.
 * Returns the character at the given index, or panics if out of bounds.
 * 
 * @param a L0 string.
 * @param index Index.
 * @return Byte value.
 *
 * L0 signature: `extern func rt_string_get(s: string, index: int) -> byte;` 
 */
static dea_byte rt_string_get(dea_string a, dea_int index) {
    dea_int a_len = rt_strlen(a);
    if (index < 0 || index >= a_len) {
        _rt_panic_fmt("rt_string_get: index %d out of bounds for string of length %d",
                      (int)index, (int)a_len);
    }
    char *a_data = _rt_string_bytes(a);
    if (a_data == NULL) {
        _rt_panic("rt_string_get: string data is null");
    }
    return (dea_byte)a_data[index];
}

/**
 * Return a pointer to the raw byte data of a string.
 *
 * @param s L0 string.
 * @return Pointer to the first byte.
 *
 * L0 signature: `extern func rt_string_bytes_ptr(s: string) -> byte*;`
 */
static dea_byte *rt_string_bytes_ptr(dea_string s) {
    return (dea_byte*)_rt_string_bytes(s);
}

/**
 * Check if two strings are equal.
 * 
 * @param a First string.
 * @param b Second string.
 * @return 1 if equal, 0 otherwise.
 *
 * L0 signature: `extern func rt_string_equals(a: string, b: string) -> bool;` 
 */
static dea_bool rt_string_equals(dea_string a, dea_string b) {
    dea_int a_len = rt_strlen(a);
    dea_int b_len = rt_strlen(b);
    if (a_len != b_len) {
        return 0;
    }
    if (a_len == 0) {
        return 1;  /* Both empty */
    }
    char *a_data = _rt_string_bytes(a);
    char *b_data = _rt_string_bytes(b);
    if (a_data == NULL || b_data == NULL) {
        _rt_panic("rt_string_equals: invalid state - string data is null");
    }
    return memcmp(a_data, b_data, (size_t)a_len) == 0 ? 1 : 0;
}

/**
 * Compare two strings lexicographically.
 * Returns 0 if equal, <0 if a < b, >0 if a > b.
 * 
 * @param a First string.
 * @param b Second string.
 * @return Comparison result.
 *
 * L0 signature: `extern func rt_string_compare(a: string, b: string) -> int;` 
 */
static dea_int rt_string_compare(dea_string a, dea_string b) {
    dea_int a_len = rt_strlen(a);
    dea_int b_len = rt_strlen(b);

    dea_int min_len = a_len;
    if (b_len < min_len) {
        min_len = b_len;
    }

    if (min_len > 0) {
        char *a_data = _rt_string_bytes(a);
        char *b_data = _rt_string_bytes(b);
        if (a_data == NULL || b_data == NULL) {
            _rt_panic("rt_string_compare: string data is null");
        }

        int result = memcmp(a_data, b_data, (size_t)min_len);
        if (result < 0) {
            return -1;
        }
        if (result > 0) {
            return 1;
        }
    }

    if (a_len < b_len) {
        return -1;
    }
    if (a_len > b_len) {
        return 1;
    }
    return 0;
}

/**
 * Concatenate two strings (allocates new memory).
 * Returns a heap-allocated string containing a + b.
 * 
 * @param a First string.
 * @param b Second string.
 * @return Concatenated string.
 *
 * L0 signature: `extern func rt_string_concat(a: string, b: string) -> string;` 
 */
#ifdef DEA_TRACE_MEMORY
static dea_string _rt_string_concat_impl(dea_string a, dea_string b, const char *_loc_file, int _loc_line) {
    dea_int a_len = rt_strlen(a);
    dea_int b_len = rt_strlen(b);
    
    /* Check for overflow in total length */
    if (a_len > INT32_MAX - b_len) {
        _rt_panic("rt_string_concat: combined length too large for dea_int");
    }

    dea_int total_len = a_len + b_len;

    if (total_len == 0) {
        return DEA_STRING_EMPTY;
    }

    dea_string s = _rt_alloc_string_impl(total_len, _loc_file, _loc_line); /* result string */
    char *s_data = _rt_string_bytes(s);
    char *a_data = _rt_string_bytes(a);
    char *b_data = _rt_string_bytes(b);
    if (s_data == NULL) {
        _rt_panic("rt_string_concat: result string data is null");
    }
    if (a_data != NULL && a_len > 0) {
        memcpy(s_data, a_data, (size_t)a_len);
    }
    if (b_data != NULL && b_len > 0) {
        memcpy(s_data + a_len, b_data, (size_t)b_len);
    }
    s_data[total_len] = '\0'; /* null-terminate */
    return s;
}
#define rt_string_concat(a, b) _rt_string_concat_impl((a), (b), __FILE__, __LINE__)
#else
static dea_string rt_string_concat(dea_string a, dea_string b) {
    dea_int a_len = rt_strlen(a);
    dea_int b_len = rt_strlen(b);
    
    /* Check for overflow in total length */
    if (a_len > INT32_MAX - b_len) {
        _rt_panic("rt_string_concat: combined length too large for dea_int");
    }

    dea_int total_len = a_len + b_len;

    if (total_len == 0) {
        return DEA_STRING_EMPTY;
    }

    dea_string s = _rt_alloc_string(total_len); /* result string */
    char *s_data = _rt_string_bytes(s);
    char *a_data = _rt_string_bytes(a);
    char *b_data = _rt_string_bytes(b);
    if (s_data == NULL) {
        _rt_panic("rt_string_concat: result string data is null");
    }
    if (a_data != NULL && a_len > 0) {
        memcpy(s_data, a_data, (size_t)a_len);
    }
    if (b_data != NULL && b_len > 0) {
        memcpy(s_data + a_len, b_data, (size_t)b_len);
    }
    s_data[total_len] = '\0'; /* null-terminate */
    return s;
}
#endif

/**
 * Create a substring (allocates new memory).
 * Panics if start/end are out of bounds or start > end.
 * 
 * @param s Source string.
 * @param start Start index.
 * @param end End index.
 * @return Slice string.
 *
 * L0 signature: `extern func rt_string_slice(s: string, start: int, end: int) -> string;` 
 */
static dea_string rt_string_slice(dea_string s, dea_int start, dea_int end) {
    dea_int s_len = rt_strlen(s);
    if (start < 0 || start > s_len) {
        _rt_panic_fmt("rt_string_slice: start %d out of bounds for string of length %d",
                     (int)start, (int)s_len);
    }
    if (end < start || end > s_len) {
        _rt_panic_fmt("rt_string_slice: end %d invalid for start %d, string length %d",
                     (int)end, (int)start, (int)s_len);
    }

    dea_int slice_len = end - start;

    if (slice_len == 0) {
        return DEA_STRING_EMPTY;
    }

    dea_string result = _rt_alloc_string(slice_len);
    char *s_data = _rt_string_bytes(s);
    char *d_data = _rt_string_bytes(result);
    memcpy(d_data, s_data + start, (size_t)slice_len);
    d_data[slice_len] = '\0';

    return result;
}

/**
 * Create an L0 string from a single character (byte).
 * Allocates a new heap string of length 1.
 * Note: Caller must free the returned string using _rt_free_string.
 * 
 * @param b Character.
 * @return L0 string.
 *
 * L0 signature: `extern func rt_string_from_byte(b: byte) -> string;` 
 */
static dea_string rt_string_from_byte(dea_byte b) {
    dea_string s = _rt_alloc_string(1);
    char *s_data = _rt_string_bytes(s);
    s_data[0] = (char)b;
    s_data[1] = '\0'; /* null-terminate */
    return s;
}

/**
 * Create an L0 string from a byte array and a length.
 * Allocates a new heap string of the given length and copies data.
 * The array does not need to be a null-terminated C string: all bytes are copied and a null
 * terminator is added for C interoperability.
 * Panics if len is negative.
 * 
 * @param bytes Pointer to bytes.
 * @param len Length.
 * @return L0 string.
 *
 * L0 signature: `extern func rt_string_from_byte_array(bytes: byte*, len: int) -> string;` 
 */
static dea_string rt_string_from_byte_array(dea_byte* bytes, dea_int len) {
    if (len < 0) {
        _rt_panic("rt_string_from_byte_array: negative length");
    }
    dea_string s = _rt_alloc_string(len);
    char *s_data = _rt_string_bytes(s);
    memcpy(s_data, bytes, (size_t)len);
    return s;
}

/**
 * Increment reference count for heap strings (no-op for static).
 * Panics if the string is heap-allocated but has an invalid refcount state (e.g. double free detected).
 * 
 * @param s L0 string.
 *
 * L0 signature: `extern func rt_string_retain(s: string) -> void;` 
 */
#ifdef DEA_TRACE_ARC
static void _rt_string_retain_impl(dea_string s, const char *_loc_file, int _loc_line) {
    if (s.kind == DEA_STRING_K_STATIC) {
        _RT_TRACE_ARC("op=retain kind=static ptr=%p rc_before=-1 rc_after=-1 action=noop loc=\"%s\":%d", (void*)s.data.s_str.bytes, _loc_file, _loc_line);
        return; /* Static strings are not reference counted */
    }
    _dea_h_string *hs = s.data.h_str;
    if (hs == NULL) {
        _RT_TRACE_ARC("op=retain kind=heap ptr=%p rc_before=-1 rc_after=-1 action=panic-null-ptr loc=\"%s\":%d", (void*)hs, _loc_file, _loc_line);
        _rt_panic("rt_string_retain: null heap string pointer");
    }
    dea_int rc_before = hs->refcount;
    if (rc_before == _RT_MEM_SENTINEL) {
        _RT_TRACE_ARC(
            "op=retain kind=heap ptr=%p rc_before=%d rc_after=%d action=panic-use-after-free loc=\"%s\":%d",
            (void*)hs, (int)rc_before, (int)rc_before, _loc_file, _loc_line
        );
        _rt_panic("rt_string_retain: use after free");
    }
    if (rc_before > 0 && rc_before < INT32_MAX - 1) {
        hs->refcount++;
        _RT_TRACE_ARC(
            "op=retain kind=heap ptr=%p rc_before=%d rc_after=%d action=retain loc=\"%s\":%d",
            (void*)hs, (int)rc_before, (int)hs->refcount, _loc_file, _loc_line
        );
    } else if (rc_before == INT32_MAX - 1) {
        _RT_TRACE_ARC(
            "op=retain kind=heap ptr=%p rc_before=%d rc_after=%d action=panic-overflow loc=\"%s\":%d",
            (void*)hs, (int)rc_before, (int)rc_before, _loc_file, _loc_line
        );
        _rt_panic_fmt("rt_string_retain: invalid refcount state: %d", (int)hs->refcount);
    } else if (hs->refcount == INT32_MAX) {
        /* Non-refcounted heap string: no-op */
        _RT_TRACE_ARC(
            "op=retain kind=heap ptr=%p rc_before=%d rc_after=%d action=noop-nonref loc=\"%s\":%d",
            (void*)hs, (int)rc_before, (int)rc_before, _loc_file, _loc_line
        );
    } else {
        _RT_TRACE_ARC(
            "op=retain kind=heap ptr=%p rc_before=%d rc_after=%d action=panic-invalid-state loc=\"%s\":%d",
            (void*)hs, (int)rc_before, (int)rc_before, _loc_file, _loc_line
        );
        _rt_panic_fmt("rt_string_retain: invalid refcount state: %d", (int)hs->refcount);
    }
}
#define rt_string_retain(s) _rt_string_retain_impl((s), __FILE__, __LINE__)
#else
static void rt_string_retain(dea_string s) {
    if (s.kind == DEA_STRING_K_STATIC) {
        _RT_TRACE_ARC("op=retain kind=static ptr=%p rc_before=-1 rc_after=-1 action=noop", (void*)s.data.s_str.bytes);
        return; /* Static strings are not reference counted */
    }
    _dea_h_string *hs = s.data.h_str;
    if (hs == NULL) {
        _RT_TRACE_ARC("op=retain kind=heap ptr=%p rc_before=-1 rc_after=-1 action=panic-null-ptr", (void*)hs);
        _rt_panic("rt_string_retain: null heap string pointer");
    }
    dea_int rc_before = hs->refcount;
    if (rc_before == _RT_MEM_SENTINEL) {
        _RT_TRACE_ARC(
            "op=retain kind=heap ptr=%p rc_before=%d rc_after=%d action=panic-use-after-free",
            (void*)hs, (int)rc_before, (int)rc_before
        );
        _rt_panic("rt_string_retain: use after free");
    }
    if (rc_before > 0 && rc_before < INT32_MAX - 1) {
        hs->refcount++;
        _RT_TRACE_ARC(
            "op=retain kind=heap ptr=%p rc_before=%d rc_after=%d action=retain",
            (void*)hs, (int)rc_before, (int)hs->refcount
        );
    } else if (rc_before == INT32_MAX - 1) {
        _RT_TRACE_ARC(
            "op=retain kind=heap ptr=%p rc_before=%d rc_after=%d action=panic-overflow",
            (void*)hs, (int)rc_before, (int)rc_before
        );
        _rt_panic_fmt("rt_string_retain: invalid refcount state: %d", (int)hs->refcount);
    } else if (hs->refcount == INT32_MAX) {
        /* Non-refcounted heap string: no-op */
        _RT_TRACE_ARC(
            "op=retain kind=heap ptr=%p rc_before=%d rc_after=%d action=noop-nonref",
            (void*)hs, (int)rc_before, (int)rc_before
        );
    } else {
        _RT_TRACE_ARC(
            "op=retain kind=heap ptr=%p rc_before=%d rc_after=%d action=panic-invalid-state",
            (void*)hs, (int)rc_before, (int)rc_before
        );
        _rt_panic_fmt("rt_string_retain: invalid refcount state: %d", (int)hs->refcount);
    }
}
#endif

/**
 * Decrement reference count, freeing if zero.
 * 
 * @param s L0 string.
 *
 * L0 signature: `extern func rt_string_release(s: string) -> void;` 
 */
#ifdef DEA_TRACE_ARC
static void _rt_string_release_impl(dea_string s, const char *_loc_file, int _loc_line) {
    _rt_free_string_impl(s, _loc_file, _loc_line);
}
#define rt_string_release(s) _rt_string_release_impl((s), __FILE__, __LINE__)
#else
static void rt_string_release(dea_string s) {
    _rt_free_string(s);
}
#endif

/* =========================================================================
 * System interaction and environment
 * ========================================================================= */

/**
 * Execute a system command and return its normalized status.
 * Returns the command exit code, `128 + signal` when terminated by a signal,
 * or a negative value on error launching the shell.
 * 
 * @param cmd Command string.
 * @return Normalized status.
 *
 * L0 signature: `extern func rt_system(cmd: string) -> int;` 
 */
static dea_int rt_system(dea_string cmd) {
    char *c = _rt_string_bytes(cmd);
    int status = system(c);
#if defined(_WIN32)
    return (dea_int)status;
#else
    if (status < 0) {
        return (dea_int)status;
    }
    if (WIFEXITED(status)) {
        return (dea_int)WEXITSTATUS(status);
    }
    if (WIFSIGNALED(status)) {
        return (dea_int)(128 + WTERMSIG(status));
    }
    return (dea_int)status;
#endif
}

/**
 * Get an environment variable as an L0 optional string.
 * Returns null (empty optional) if the variable is not set.
 * 
 * @param name Variable name.
 * @return Optional string value.
 *
 * L0 signature: `extern func rt_get_env_var(name: string) -> string?;` 
 */
static dea_opt_string rt_get_env_var(dea_string name) {
    if (rt_strlen(name) == 0) {
        return DEA_OPT_STRING_NULL;
    }

    /* Get the underlying null-terminated char[] */
    char *c_name = _rt_string_bytes(name);
    if (c_name == NULL) {
        return DEA_OPT_STRING_NULL;
    }

    /* Get environment variable */
    char *c_value = getenv(c_name);

    if (c_value == NULL) {
        return DEA_OPT_STRING_NULL;
    }

    /* Convert value to L0 string*? */
    dea_string result = _rt_new_dea_string(c_value);
    return (dea_opt_string){ .has_value = 1, .value = result };
}

/**
 * Get the number of command-line arguments.
 * 
 * @return Argument count.
 *
 * L0 signature: `extern func rt_get_argc() -> int;` 
 */
static dea_int rt_get_argc(void) {
    return (dea_int)_rt_argc;
}

/**
 * Convert a native process identifier into `dea_int`.
 *
 * @param value Native process identifier.
 * @param out Output location.
 * @return 1 when `value` fits in `dea_int`, otherwise 0.
 */
static dea_bool _rt_pid_to_dea_int(intmax_t value, dea_int *out) {
    if (value < 0 || value > INT32_MAX) {
        return 0;
    }
    *out = (dea_int)value;
    return 1;
}

/**
 * Get the current process identifier.
 *
 * @return Process identifier.
 *
 * L0 signature: `extern func rt_get_pid() -> int;`
 */
static dea_int rt_get_pid(void) {
    dea_int out = 0;
#if defined(_WIN32)
    if (!_rt_pid_to_dea_int((intmax_t)_getpid(), &out)) {
        _rt_panic("rt_get_pid: process identifier does not fit in dea_int");
    }
#else
    if (!_rt_pid_to_dea_int((intmax_t)getpid(), &out)) {
        _rt_panic("rt_get_pid: process identifier does not fit in dea_int");
    }
#endif
    return out;
}

/**
 * Get the command-line argument at the given index.
 * Panics if index is out of bounds.
 * 
 * @param i Index.
 * @return Argument string.
 *
 * L0 signature: `extern func rt_get_argv(i: int) -> string;` 
 */
static dea_string rt_get_argv(dea_int i) {
    if (i < 0 || i >= _rt_argc) {
        _rt_panic_fmt("rt_get_argv: index %d out of bounds (argc=%d)", (int)i, _rt_argc);
    }
    return _rt_dea_string_from_const_literal(_rt_argv[i]);
}

/* =========================================================================
 * Time APIs
 * ========================================================================= */

/**
 * Internal helper to convert time_t to dea_int seconds.
 */
static dea_bool _rt_time_to_dea_int_sec(time_t value, dea_int *out) {
    long long sec = (long long)value;
    if (sec < INT32_MIN || sec > INT32_MAX) {
        return 0;
    }
    *out = (dea_int)sec;
    return 1;
}

/**
 * Internal helper to convert long to dea_int nanoseconds.
 */
static dea_bool _rt_time_to_dea_int_nsec(long value, dea_int *out) {
    long long nsec = (long long)value;
    if (nsec < 0 || nsec > 999999999LL) {
        return 0;
    }
    *out = (dea_int)nsec;
    return 1;
}

/**
 * Internal helper to write time parts to struct.
 */
static dea_bool _rt_time_write_parts(struct dea_sys_rt_RtTimeParts *out, dea_int sec, dea_int nsec) {
    if (out == NULL) {
        _rt_panic("_rt_time_write_parts: out-parameter is null");
    }
    out->sec = sec;
    out->nsec = nsec;
    return 1;
}

/**
 * Capture current unix wall clock into `out`.
 * 
 * @param out Pointer to RtTimeParts.
 * @return 1 on success, 0 on failure.
 *
 * L0 signature: `extern func rt_time_unix(out: RtTimeParts*) -> bool;` 
 */
static dea_bool rt_time_unix(struct dea_sys_rt_RtTimeParts *out) {
    if (out == NULL) {
        _rt_panic("rt_time_unix: out-parameter is null");
    }

#if defined(CLOCK_REALTIME)
    struct timespec ts;
    if (clock_gettime(CLOCK_REALTIME, &ts) == 0) {
        dea_int sec = 0;
        dea_int nsec = 0;
        if (!_rt_time_to_dea_int_sec(ts.tv_sec, &sec)) {
            return 0;
        }
        if (!_rt_time_to_dea_int_nsec(ts.tv_nsec, &nsec)) {
            return 0;
        }
        return _rt_time_write_parts(out, sec, nsec);
    }
#endif

    time_t now = time(NULL);
    if (now == (time_t)-1) {
        return 0;
    }

    dea_int sec = 0;
    if (!_rt_time_to_dea_int_sec(now, &sec)) {
        return 0;
    }
    return _rt_time_write_parts(out, sec, 0);
}

/**
 * Capture current monotonic clock into `out`.
 * 
 * @param out Pointer to RtTimeParts.
 * @return 1 on success, 0 on failure.
 *
 * L0 signature: `extern func rt_time_monotonic(out: RtTimeParts*) -> bool;` 
 */
static dea_bool rt_time_monotonic(struct dea_sys_rt_RtTimeParts *out) {
    if (out == NULL) {
        _rt_panic("rt_time_monotonic: out-parameter is null");
    }

#if defined(CLOCK_MONOTONIC)
    struct timespec ts;
    if (clock_gettime(CLOCK_MONOTONIC, &ts) != 0) {
        return 0;
    }

    dea_int sec = 0;
    dea_int nsec = 0;
    if (!_rt_time_to_dea_int_sec(ts.tv_sec, &sec)) {
        return 0;
    }
    if (!_rt_time_to_dea_int_nsec(ts.tv_nsec, &nsec)) {
        return 0;
    }
    return _rt_time_write_parts(out, sec, nsec);
#else
    (void)out;
    return 0;
#endif
}

/**
 * Returns whether a monotonic clock source is available.
 * 
 * @return 1 if supported, 0 otherwise.
 *
 * L0 signature: `extern func rt_time_monotonic_supported() -> bool;` 
 */
static dea_bool rt_time_monotonic_supported(void) {
#if defined(CLOCK_MONOTONIC)
    return 1;
#else
    return 0;
#endif
}

/**
 * Returns local UTC offset in seconds for `unix_sec`.
 *
 * Computes the offset by comparing `gmtime` and `localtime` breakdowns
 * directly, avoiding `mktime` which rejects pre-epoch values on some platforms.
 *
 * @param unix_sec Unix timestamp.
 * @return Optional integer offset.
 *
 * L0 signature: `extern func rt_time_local_offset_sec(unix_sec: int) -> int?;`
 */
static dea_opt_int rt_time_local_offset_sec(dea_int unix_sec) {
    time_t t = (time_t)unix_sec;
    if ((dea_int)t != unix_sec) {
        return (dea_opt_int){ .has_value = 0 };
    }

    struct tm *utc_ptr = gmtime(&t);
    if (utc_ptr == NULL) {
        return (dea_opt_int){ .has_value = 0 };
    }
    struct tm utc_tm = *utc_ptr;

    struct tm *local_ptr = localtime(&t);
    if (local_ptr == NULL) {
        return (dea_opt_int){ .has_value = 0 };
    }
    struct tm local_tm = *local_ptr;

    /* Day difference: can only be -1, 0, or +1 for timezone offsets. */
    int day_diff;
    if (local_tm.tm_year > utc_tm.tm_year) {
        day_diff = 1;
    } else if (local_tm.tm_year < utc_tm.tm_year) {
        day_diff = -1;
    } else {
        day_diff = local_tm.tm_yday - utc_tm.tm_yday;
    }

    long long offset = (long long)day_diff * 86400
                     + (long long)(local_tm.tm_hour - utc_tm.tm_hour) * 3600
                     + (long long)(local_tm.tm_min - utc_tm.tm_min) * 60
                     + (long long)(local_tm.tm_sec - utc_tm.tm_sec);
    if (offset < INT32_MIN || offset > INT32_MAX) {
        return (dea_opt_int){ .has_value = 0 };
    }

    return (dea_opt_int){ .has_value = 1, .value = (dea_int)offset };
}

/**
 * Returns whether local time is daylight-saving time for `unix_sec`.
 * 
 * @param unix_sec Unix timestamp.
 * @return Optional boolean.
 *
 * L0 signature: `extern func rt_time_local_is_dst(unix_sec: int) -> bool?;` 
 */
static dea_opt_bool rt_time_local_is_dst(dea_int unix_sec) {
    time_t t = (time_t)unix_sec;
    if ((dea_int)t != unix_sec) {
        return (dea_opt_bool){ .has_value = 0 };
    }

    struct tm *local_ptr = localtime(&t);
    if (local_ptr == NULL) {
        return (dea_opt_bool){ .has_value = 0 };
    }

    if (local_ptr->tm_isdst < 0) {
        return (dea_opt_bool){ .has_value = 0 };
    }
    return (dea_opt_bool){ .has_value = 1, .value = local_ptr->tm_isdst > 0 ? 1 : 0 };
}

/* =========================================================================
 * I/O operations (whole-file)
 * ========================================================================= */

/**
 * Read entire file contents into a string.
 * Returns empty string on error (file not found, read error, allocation failure).
 * 
 * @param path File path.
 * @return Optional string containing file contents.
 *
 * L0 signature: `extern func rt_read_file_all(path: string) -> string?;` 
 */
static dea_opt_string rt_read_file_all(dea_string path) {

    dea_int path_len = rt_strlen(path);

    if (path_len == 0) {
        return DEA_OPT_STRING_NULL;
    }

    char *path_cstr = _rt_string_bytes(path);
    struct stat st;

    if (stat(path_cstr, &st) != 0) {
        return DEA_OPT_STRING_NULL;
    }
    if (!S_ISREG(st.st_mode)) {
        return DEA_OPT_STRING_NULL;
    }
    if (st.st_size < 0 || (uint64_t)st.st_size > INT32_MAX) {
        return DEA_OPT_STRING_NULL;
    }

    FILE *file = fopen(path_cstr, "rb");
    if (file == NULL) {
        return DEA_OPT_STRING_NULL;
    }

    size_t size = (size_t)st.st_size;

    dea_string result = _rt_alloc_string((dea_int)size);
    char *buffer = _rt_string_bytes(result);

    /* Read file contents */
    size_t bytes_read = fread(buffer, 1, size, file);
    fclose(file);

    if (bytes_read != size) {
        _rt_free_string(result);
        return DEA_OPT_STRING_NULL;
    }

    return (dea_opt_string){ .has_value = 1, .value = result };
}

/**
 * Write string data to a file.
 * Returns 1 (true) on success, 0 (false) on error.
 * 
 * @param path File path.
 * @param data Data string.
 * @return 1 on success, 0 on failure.
 *
 * L0 signature: `extern func rt_write_file_all(path: string, data: string) -> bool;` 
 */
static dea_bool rt_write_file_all(dea_string path, dea_string data) {
    dea_int path_len = rt_strlen(path);
    if (path_len == 0) {
        return 0;
    }

    /* Ensure path is null-terminated for fopen */
    char *path_cstr = _rt_string_bytes(path);
    FILE *file = fopen(path_cstr, "wb");
    if (file == NULL) {
        return 0;
    }

    dea_int data_len = rt_strlen(data);
    char *data_b = _rt_string_bytes(data);
    if (data_len > 0) {
        size_t written = fwrite(data_b, 1, (size_t)data_len, file);
        int close_result = fclose(file);

        if (written != (size_t)data_len || close_result != 0) {
            return 0;
        }
    } else {
        fclose(file);
    }

    return 1;
}

/**
 * Return basic metadata for a path.
 * 
 * @param path File path.
 * @return Metadata record with nullable size and mtime fields.
 *
 * L0 signature: `extern func rt_file_info(path: string) -> RtFileInfo;`
 */
static struct dea_sys_rt_RtFileInfo rt_file_info(dea_string path) {
    struct dea_sys_rt_RtFileInfo out = {
        .exists = 0,
        .is_file = 0,
        .is_dir = 0,
        .size = { .has_value = 0 },
        .mtime_sec = { .has_value = 0 },
        .mtime_nsec = { .has_value = 0 },
    };
    char *c = _rt_string_bytes(path);
#if defined(_WIN32)
    struct _stat64 st;
    if (_stat64(c, &st) != 0) {
        return out;
    }

    out.exists = 1;
    out.is_file = (st.st_mode & _S_IFREG) ? 1 : 0;
    out.is_dir = (st.st_mode & _S_IFDIR) ? 1 : 0;

    if (st.st_size >= 0 && (__int64)(dea_int)st.st_size == st.st_size) {
        out.size = (dea_opt_int){ .has_value = 1, .value = (dea_int)st.st_size };
    }
    if ((time_t)(dea_int)st.st_mtime == st.st_mtime) {
        out.mtime_sec = (dea_opt_int){ .has_value = 1, .value = (dea_int)st.st_mtime };
    }
    return out;
#else
    struct stat st;
    if (stat(c, &st) != 0) {
        return out;
    }

    out.exists = 1;
    out.is_file = S_ISREG(st.st_mode) ? 1 : 0;
    out.is_dir = S_ISDIR(st.st_mode) ? 1 : 0;

    if (st.st_size >= 0 && (off_t)(dea_int)st.st_size == st.st_size) {
        out.size = (dea_opt_int){ .has_value = 1, .value = (dea_int)st.st_size };
    }
    if ((time_t)(dea_int)st.st_mtime == st.st_mtime) {
        out.mtime_sec = (dea_opt_int){ .has_value = 1, .value = (dea_int)st.st_mtime };
#if defined(__APPLE__)
        if ((long)(dea_int)st.st_mtimespec.tv_nsec == st.st_mtimespec.tv_nsec) {
            out.mtime_nsec = (dea_opt_int){ .has_value = 1, .value = (dea_int)st.st_mtimespec.tv_nsec };
        }
#elif defined(_POSIX_C_SOURCE) && _POSIX_C_SOURCE >= 200809L
        if ((long)(dea_int)st.st_mtim.tv_nsec == st.st_mtim.tv_nsec) {
            out.mtime_nsec = (dea_opt_int){ .has_value = 1, .value = (dea_int)st.st_mtim.tv_nsec };
        }
#endif
    }
    return out;
#endif
}

/**
 * Delete the file at the given path.
 * Returns 1 (true) on success, 0 (false) on error.
 * 
 * @param path File path.
 * @return 1 on success, 0 on failure.
 *
 * L0 signature: `extern func rt_delete_file(path: string) -> bool;` 
 */
static dea_bool rt_delete_file(dea_string path) {
    char *c = _rt_string_bytes(path);
    int result = remove(c);
    return result == 0;
}

/**
 * Write raw bytes to one standard stream.
 *
 * @param stream Target stream.
 * @param buf Source bytes.
 * @param len Maximum number of bytes to write.
 * @return Bytes written, or `-1` on error.
 */
static dea_int _rt_stream_write_some(FILE *stream, const dea_byte *buf, dea_int len) {
    if (len < 0) {
        return -1;
    }
    if (len == 0) {
        return 0;
    }
    if (buf == NULL) {
        return -1;
    }

    clearerr(stream);
    size_t written = fwrite(buf, 1, (size_t)len, stream);
    if (written == 0 && ferror(stream)) {
        return -1;
    }
    return (dea_int)written;
}

/**
 * Read raw bytes from standard input.
 *
 * @param buf Destination bytes.
 * @param capacity Maximum number of bytes to read.
 * @return Bytes read, `0` on EOF, or `-1` on error.
 *
 * L0 signature: `extern func rt_stdin_read(buf: byte*, capacity: int) -> int;`
 */
static dea_int rt_stdin_read(dea_byte *buf, dea_int capacity) {
    if (capacity < 0) {
        return -1;
    }
    if (capacity == 0) {
        return 0;
    }
    if (buf == NULL) {
        return -1;
    }

    clearerr(stdin);
    size_t nread = fread(buf, 1, (size_t)capacity, stdin);
    if (nread == 0 && ferror(stdin)) {
        return -1;
    }
    return (dea_int)nread;
}

/**
 * Write raw bytes to standard output.
 *
 * @param buf Source bytes.
 * @param len Maximum number of bytes to write.
 * @return Bytes written, or `-1` on error.
 *
 * L0 signature: `extern func rt_stdout_write(buf: byte*, len: int) -> int;`
 */
static dea_int rt_stdout_write(dea_byte *buf, dea_int len) {
    return _rt_stream_write_some(stdout, buf, len);
}

/**
 * Write raw bytes to standard error.
 *
 * @param buf Source bytes.
 * @param len Maximum number of bytes to write.
 * @return Bytes written, or `-1` on error.
 *
 * L0 signature: `extern func rt_stderr_write(buf: byte*, len: int) -> int;`
 */
static dea_int rt_stderr_write(dea_byte *buf, dea_int len) {
    return _rt_stream_write_some(stderr, buf, len);
}

/* =========================================================================
 * Printing to stdout/stderr
 * ========================================================================= */

/**
 * Flush stdout. */
static void rt_flush_stdout(void) {
    fflush(stdout);
}

/**
 * Flush stderr.
 *

 * L0 signature: `extern func rt_flush_stdout() -> void;`
 *
 * L0 signature: `extern func rt_flush_stderr() -> void;` 
 */
static void rt_flush_stderr(void) {
    fflush(stderr);
}

/**
 * Internal helper to print a dea_string to a given stream.
 * 
 * @param s String to print.
 * @param stream Target stream.
 */
void _rt_print(dea_string s, FILE *stream){
    dea_int s_len = rt_strlen(s);
    char *s_data = _rt_string_bytes(s);
    if (s_len > 0 && s_data != NULL) {
        fwrite(s_data, 1, (size_t)s_len, stream);
    }
}

/**
 * Print a string to stdout.
 * 
 * @param s String to print.
 *
 * L0 signature: `extern func rt_print(s: string) -> void;` 
 */
static void rt_print(dea_string s) {
    _rt_print(s, stdout);
}

/**
 * Print a string to stderr.
 * 
 * @param s String to print.
 *
 * L0 signature: `extern func rt_print_stderr(s: string) -> void;` 
 */
static void rt_print_stderr(dea_string s) {
    _rt_print(s, stderr);
}

/**
 * Print a newline to stdout. */
static void rt_println(void) {
    fputc('\n', stdout);
}

/**
 * Print a newline to stderr.
 *

 * L0 signature: `extern func rt_println() -> void;`
 *
 * L0 signature: `extern func rt_println_stderr() -> void;` 
 */
static void rt_println_stderr(void) {
    fputc('\n', stderr);
}

/**
 * Print an integer to stdout.
 * 
 * @param x Integer value.
 *
 * L0 signature: `extern func rt_print_int(x: int) -> void;` 
 */
static void rt_print_int(dea_int x) {
    printf("%d", (int)x);
}

/**
 * Print an unsigned integer to stdout.
 *
 * @param x Unsigned integer value.
 *
 * L0 signature: `extern func rt_print_uint(x: uint) -> void;`
 */
static void rt_print_uint(dea_uint x) {
    printf("%" PRIu32, (uint32_t)x);
}

/**
 * Print a long integer to stdout.
 *
 * @param x Long integer value.
 *
 * L0 signature: `extern func rt_print_long(x: long) -> void;`
 */
static void rt_print_long(dea_long x) {
    printf("%" PRId64, (int64_t)x);
}

/**
 * Print an unsigned long integer to stdout.
 *
 * @param x Unsigned long integer value.
 *
 * L0 signature: `extern func rt_print_ulong(x: ulong) -> void;`
 */
static void rt_print_ulong(dea_ulong x) {
    printf("%" PRIu64, (uint64_t)x);
}

/**
 * Print a float to stdout.
 *
 * @param x Float value.
 *
 * L0 signature: `extern func rt_print_float(x: float) -> void;`
 */
static void rt_print_float(dea_float x) {
    printf("%.9g", (double)x);
}

/**
 * Print a double to stdout.
 *
 * @param x Double value.
 *
 * L0 signature: `extern func rt_print_double(x: double) -> void;`
 */
static void rt_print_double(dea_double x) {
    printf("%.17g", (double)x);
}

/**
 * Print an integer to stderr.
 * 
 * @param x Integer value.
 *
 * L0 signature: `extern func rt_print_int_stderr(x: int) -> void;` 
 */
static void rt_print_int_stderr(dea_int x) {
    fprintf(stderr, "%d", (int)x);
}

/**
 * Print an unsigned integer to stderr.
 *
 * @param x Unsigned integer value.
 *
 * L0 signature: `extern func rt_print_uint_stderr(x: uint) -> void;`
 */
static void rt_print_uint_stderr(dea_uint x) {
    fprintf(stderr, "%" PRIu32, (uint32_t)x);
}

/**
 * Print a long integer to stderr.
 *
 * @param x Long integer value.
 *
 * L0 signature: `extern func rt_print_long_stderr(x: long) -> void;`
 */
static void rt_print_long_stderr(dea_long x) {
    fprintf(stderr, "%" PRId64, (int64_t)x);
}

/**
 * Print an unsigned long integer to stderr.
 *
 * @param x Unsigned long integer value.
 *
 * L0 signature: `extern func rt_print_ulong_stderr(x: ulong) -> void;`
 */
static void rt_print_ulong_stderr(dea_ulong x) {
    fprintf(stderr, "%" PRIu64, (uint64_t)x);
}

/**
 * Print a float to stderr.
 *
 * @param x Float value.
 *
 * L0 signature: `extern func rt_print_float_stderr(x: float) -> void;`
 */
static void rt_print_float_stderr(dea_float x) {
    fprintf(stderr, "%.9g", (double)x);
}

/**
 * Print a double to stderr.
 *
 * @param x Double value.
 *
 * L0 signature: `extern func rt_print_double_stderr(x: double) -> void;`
 */
static void rt_print_double_stderr(dea_double x) {
    fprintf(stderr, "%.17g", (double)x);
}

/**
 * Print a bool to stdout.
 * 
 * @param x Boolean value.
 *
 * L0 signature: `extern func rt_print_bool(x: bool) -> void;` 
 */
static void rt_print_bool(dea_bool x) {
    printf("%s", x ? "true" : "false");
}

/**
 * Print a bool to stderr.
 * 
 * @param x Boolean value.
 *
 * L0 signature: `extern func rt_print_bool_stderr(x: bool) -> void;` 
 */
static void rt_print_bool_stderr(dea_bool x) {
    fprintf(stderr, "%s", x ? "true" : "false");
}

/* =========================================================================
 * Reading from stdin
 * ========================================================================= */

/**
 * Read a line from stdin into a dynamically allocated buffer.
 * Returns None on EOF (no characters read).
 * *
 * Ownership: on Some(s), s.data is heap-allocated and must be freed by calling
 * rt_string_release(s) (directly or indirectly via stdlib).
 * 
 * @return Optional string containing the line.
 *
 * L0 signature: `extern func rt_read_line() -> string?;` 
 */
static dea_opt_string rt_read_line(void) {
    size_t capacity = 128;
    size_t length = 0;

    dea_string s = _rt_alloc_string(capacity);
    char *s_data = _rt_string_bytes(s);

    int c;
    while ((c = fgetc(stdin)) != EOF && c != '\n') {
        if (length + 1 >= capacity) {
            capacity = capacity * 2;
            s = _rt_realloc_string(s, (dea_int)capacity);
            s_data = _rt_string_bytes(s);
        }
        s_data[length++] = (char)c;
    }

    /* EOF with no data => None */
    if (c == EOF && length == 0) {
        _rt_free_string(s);
        return DEA_OPT_STRING_NULL;
    }

    if (length > INT32_MAX) {
        _rt_free_string(s);
        _rt_panic("rt_read_line: line too long for dea_int");
    }

    /* Empty line => Some(empty string) without allocating owned storage. */
    if (length == 0) {
        _rt_free_string(s);
        return DEA_OPT_STRING_EMPTY;
    }

    /* Trim string to actual length */
    if ((size_t)length < capacity) {
        s = _rt_realloc_string(s, (dea_int)length);
    }

    return (dea_opt_string){ .has_value = 1, .value = s };
}


/**
 * Read one character from stdin.
 * Returns -1 on EOF or error.
 * 
 * @return Character value or -1.
 *
 * L0 signature: `extern func rt_read_char() -> int;` 
 */
static dea_int rt_read_char(void) {
    int c = fgetc(stdin);
    if (c == EOF) {
        return -1;
    }
    return (dea_int)c;
}

/* =========================================================================
 * Other runtime utilities
 * ========================================================================= */

/**
 * Abort the program with a panic message.
 * 
 * @param message Panic message.
 *
 * L0 signature: `extern func rt_abort(message: string) -> void;` 
 */
static void rt_abort(dea_string message) {
    if (rt_strlen(message) == 0) {
        _rt_panic(NULL);
    } else {
        _rt_panic_fmt("%s", _rt_string_bytes(message));
    }
    abort();
}

/**
 * Exit the program with the given exit code.
 * 
 * @param code Exit code.
 *
 * L0 signature: `extern func rt_exit(code: int) -> void;` 
 */
static void rt_exit(dea_int code) {
    exit((int)code);
}

/* =========================================================================
 * Random number generation
 * ========================================================================= */

/**
 * Seed the random number generator.
 * Uses current time if seed is 0.
 * 
 * @param seed Seed value.
 *
 * L0 signature: `extern func rt_srand(seed: int) -> void;` 
 */
static void rt_srand(dea_int seed) {
    if (seed == 0) {
        srand((unsigned int)time(NULL));
    } else {
        srand((unsigned int)seed);
    }
}

/**
 * Generate a random integer in the range [0, max).
 * Returns 0 if max <= 0.
 * 
 * @param max Upper bound (exclusive).
 * @return Random value.
 *
 * L0 signature: `extern func rt_rand(max: int) -> int;` 
 */
static dea_int rt_rand(dea_int max) {
    if (max <= 0) {
        return 0;
    }
    return (dea_int)(rand() % max);
}

/**
 * Get the current errno value.
 * 
 * @return errno value.
 *
 * L0 signature: `extern func rt_errno() -> int;` 
 */
static dea_int rt_errno(void) {
    return (dea_int)errno;
}

/* =========================================================================
 * UNSAFE ZONE: HERE BE DRAGONS
 * ----------------------------------------------------------------------------
 * This section contains functions that directly manipulate memory.
 * Use with caution - these functions do not perform safety checks beyond basic
 * validation of input parameters.
 * They are intended for low-level operations where performance is critical.
 * Misuse can lead to undefined behavior, memory corruption, or security
 * vulnerabilities.
 * ========================================================================= */

/* =========================================================================
 * Memory allocation and manipulation functions.
 * ========================================================================= */

/**
 * Allocate memory of the given size in bytes.
 * Returns NULL on allocation failure or if bytes is zero.
 * Panics if bytes is negative, or too large to fit in size_t (platform-dependent).
 * 
 * @param bytes Size in bytes.
 * @return Pointer to allocated memory or NULL.
 *
 * L0 signature: `extern func rt_alloc(bytes: int) -> void*?;` 
 */
#ifdef DEA_TRACE_MEMORY
static void *_rt_alloc_impl(dea_int bytes, const char *_loc_file, int _loc_line) {
    /* zero-size allocations are not allowed */
    if (bytes <= 0) {
        _rt_panic("rt_alloc: invalid allocation size");
    }

    /* Check for overflow when converting to size_t */
    if ((uint64_t)bytes > SIZE_MAX) {
        _rt_panic_fmt("rt_alloc: allocation size overflow (%d bytes requested)", (int)bytes);
    }

    size_t size = (size_t)bytes;
    void *ptr = malloc(size);

    if (ptr == NULL) {
        /* Allocation failed - return NULL and let caller handle it */
        _RT_TRACE_MEM("op=alloc bytes=%d ptr=%p action=fail loc=\"%s\":%d", (int)bytes, (void*)ptr, _loc_file, _loc_line);
        return NULL;
    }

    _RT_TRACE_MEM("op=alloc bytes=%d ptr=%p action=ok loc=\"%s\":%d", (int)bytes, ptr, _loc_file, _loc_line);
    return ptr;
}
#define rt_alloc(bytes) _rt_alloc_impl((bytes), __FILE__, __LINE__)
#else
static void *rt_alloc(dea_int bytes) {
    /* zero-size allocations are not allowed */
    if (bytes <= 0) {
        _rt_panic("rt_alloc: invalid allocation size");
    }

    /* Check for overflow when converting to size_t */
    if ((uint64_t)bytes > SIZE_MAX) {
        _rt_panic_fmt("rt_alloc: allocation size overflow (%d bytes requested)", (int)bytes);
    }

    size_t size = (size_t)bytes;
    void *ptr = malloc(size);

    if (ptr == NULL) {
        /* Allocation failed - return NULL and let caller handle it */
        _RT_TRACE_MEM("op=alloc bytes=%d ptr=%p action=fail", (int)bytes, (void*)ptr);
        return NULL;
    }

    _RT_TRACE_MEM("op=alloc bytes=%d ptr=%p action=ok", (int)bytes, ptr);
    return ptr;
}
#endif

/**
 * Reallocate memory to a new size.
 * Returns NULL on failure.
 * Panics if new_bytes is negative or too large to fit in size_t (platform-dependent).
 * If ptr is NULL, behaves like rt_alloc.
 * 
 * @param ptr Pointer to memory.
 * @param new_bytes New size.
 * @return Pointer to reallocated memory or NULL.
 *
 * L0 signature: `extern func rt_realloc(ptr: void*, new_bytes: int) -> void*?;` 
 */
#ifdef DEA_TRACE_MEMORY
static void *_rt_realloc_impl(void *ptr, dea_int new_bytes, const char *_loc_file, int _loc_line) {
    /* zero-size allocations are not allowed */
    if (new_bytes <= 0) {
        _rt_panic("rt_realloc: invalid allocation size");
    }

    if ((uint64_t)new_bytes > SIZE_MAX) {
        _rt_panic_fmt("rt_realloc: allocation size overflow (%d bytes requested)", (int)new_bytes);
    }

    volatile uintptr_t old_ptr_addr = (uintptr_t)ptr;
    size_t new_size = (size_t)new_bytes;
    void *new_ptr = realloc((void*)old_ptr_addr, new_size);

    if (new_ptr == NULL) {
        /* Real failure! original pointer is still valid */
        _RT_TRACE_MEM("op=realloc old_ptr=%p bytes=%d new_ptr=%p action=fail loc=\"%s\":%d", (void*)old_ptr_addr, (int)new_bytes, (void*)new_ptr, _loc_file, _loc_line);
        return NULL;
    }

    _RT_TRACE_MEM("op=realloc old_ptr=%p bytes=%d new_ptr=%p action=ok loc=\"%s\":%d", (void*)old_ptr_addr, (int)new_bytes, new_ptr, _loc_file, _loc_line);
    return new_ptr;
}
#define rt_realloc(ptr, new_bytes) _rt_realloc_impl((ptr), (new_bytes), __FILE__, __LINE__)
#else
static void *rt_realloc(void *ptr, dea_int new_bytes) {
    /* zero-size allocations are not allowed */
    if (new_bytes <= 0) {
        _rt_panic("rt_realloc: invalid allocation size");
    }

    if ((uint64_t)new_bytes > SIZE_MAX) {
        _rt_panic_fmt("rt_realloc: allocation size overflow (%d bytes requested)", (int)new_bytes);
    }

    volatile uintptr_t old_ptr_addr = (uintptr_t)ptr;
    size_t new_size = (size_t)new_bytes;
    void *new_ptr = realloc((void*)old_ptr_addr, new_size);

    if (new_ptr == NULL) {
        /* Real failure! original pointer is still valid */
        _RT_TRACE_MEM("op=realloc old_ptr=%p bytes=%d new_ptr=%p action=fail", (void*)old_ptr_addr, (int)new_bytes, (void*)new_ptr);
        return NULL;
    }

    _RT_TRACE_MEM("op=realloc old_ptr=%p bytes=%d new_ptr=%p action=ok", (void*)old_ptr_addr, (int)new_bytes, new_ptr);
    return new_ptr;
}
#endif

/**
 * Free previously allocated memory.
 * 
 * @param ptr Pointer to free.
 *
 * L0 signature: `extern func rt_free(ptr: void*?) -> void;` 
 */
#ifdef DEA_TRACE_MEMORY
static void _rt_free_impl(void *ptr, const char *_loc_file, int _loc_line) {
    /* free(NULL) is a no-op in C */
    _RT_TRACE_MEM("op=free ptr=%p action=call loc=\"%s\":%d", ptr, _loc_file, _loc_line);
    free(ptr);
}
#define rt_free(ptr) _rt_free_impl((ptr), __FILE__, __LINE__)
#else
static void rt_free(void *ptr) {
    /* free(NULL) is a no-op in C */
    _RT_TRACE_MEM("op=free ptr=%p action=call", ptr);
    free(ptr);
}
#endif

/**
 * Allocate zeroed memory for an array of elements.
 * Returns NULL on allocation failure or if count/elem_size is negative.
 * 
 * @param count Number of elements.
 * @param elem_size Element size.
 * @return Pointer to zeroed memory or NULL.
 *
 * L0 signature: `extern func rt_calloc(count: int, elem_size: int) -> void*?;` 
 */
#ifdef DEA_TRACE_MEMORY
static void *_rt_calloc_impl(dea_int count, dea_int elem_size, const char *_loc_file, int _loc_line) {
    if (count <= 0 || elem_size <= 0) {
        _rt_panic("rt_calloc: invalid count or element size");
    }

    /* Check for overflow in multiplication*/
    if ((uint64_t)count * (uint64_t)elem_size > SIZE_MAX) {
        _rt_panic_fmt("rt_calloc: allocation size overflow (%d elements of size %d requested)",
                     (int)count, (int)elem_size);
    }

    size_t n = (size_t)count;
    size_t size = (size_t)elem_size;

    void *ptr = calloc(n, size);
    _RT_TRACE_MEM(
        "op=calloc count=%d elem_size=%d ptr=%p action=%s loc=\"%s\":%d",
        (int)count, (int)elem_size, ptr, ptr == NULL ? "fail" : "ok", _loc_file, _loc_line
    );
    return ptr;
}
#define rt_calloc(count, elem_size) _rt_calloc_impl((count), (elem_size), __FILE__, __LINE__)
#else
static void *rt_calloc(dea_int count, dea_int elem_size) {
    if (count <= 0 || elem_size <= 0) {
        _rt_panic("rt_calloc: invalid count or element size");
    }

    /* Check for overflow in multiplication*/
    if ((uint64_t)count * (uint64_t)elem_size > SIZE_MAX) {
        _rt_panic_fmt("rt_calloc: allocation size overflow (%d elements of size %d requested)",
                     (int)count, (int)elem_size);
    }

    size_t n = (size_t)count;
    size_t size = (size_t)elem_size;

    void *ptr = calloc(n, size);
    _RT_TRACE_MEM(
        "op=calloc count=%d elem_size=%d ptr=%p action=%s",
        (int)count, (int)elem_size, ptr, ptr == NULL ? "fail" : "ok"
    );
    return ptr;
}
#endif

/**
 * Set memory to a specific byte value.
 * Returns destination pointer.
 * 
 * @param dest Destination pointer.
 * @param value Byte value.
 * @param bytes Number of bytes.
 * @return dest.
 *
 * L0 signature: `extern func rt_memset(dest: void*, value: int, bytes: int) -> void*;` 
 */
static void *rt_memset(void *dest, dea_int value, dea_int bytes) {
    if (bytes < 0) {
        _rt_panic("rt_memset: negative byte count");
    }

    if (bytes == 0 || dest == NULL) {
        return dest;
    }

    size_t n = (size_t)bytes;
    int c = (int)value;
    return memset(dest, c, n);
}

/**
 * Copy memory from source to destination.
 * Returns destination pointer.
 * 
 * @param dest Destination.
 * @param src Source.
 * @param bytes Number of bytes.
 * @return dest.
 *
 * L0 signature: `extern func rt_memcpy(dest: void*, src: void*, bytes: int) -> void*;` 
 */
static void *rt_memcpy(void *dest, void *src, dea_int bytes) {
    if (bytes < 0) {
        _rt_panic("rt_memcpy: negative byte count");
    }

    if (bytes == 0 || dest == NULL || src == NULL) {
        return dest;
    }

    size_t n = (size_t)bytes;
    return memcpy(dest, src, n);
}

/**
 * Compare two memory regions.
 * Returns 0 if equal, <0 if a < b, >0 if a > b.
 * 
 * @param a First region.
 * @param b Second region.
 * @param bytes Number of bytes.
 * @return Comparison result.
 *
 * L0 signature: `extern func rt_memcmp(a: void*, b: void*, bytes: int) -> int;` 
 */
static dea_int rt_memcmp(void *a, void *b, dea_int bytes) {
    if (bytes < 0) {
        _rt_panic("rt_memcmp: negative byte count");
    }

    if (bytes == 0 || a == NULL || b == NULL) {
        return 0;
    }

    size_t n = (size_t)bytes;
    int result = memcmp(a, b, n);
    if (result < 0) {
        return -1;
    } else if (result > 0) {
        return 1;
    } else {
        return 0;
    }
}

/**
 * Get a pointer to an element in an array.
 * Panics if array_data is NULL, element_size is non-positive, or index is negative.
 * 
 * @param array_data Pointer to array data.
 * @param element_size Size of one element.
 * @param index Element index.
 * @return Pointer to the element.
 *
 * L0 signature: `extern func rt_array_element(array_data: void*, element_size: int, index: int) -> void*;` 
 */
static void *rt_array_element(void *array_data, dea_int element_size, dea_int index) {
    if (array_data == NULL) {
        _rt_panic("rt_array_element: null array data pointer");
    }
    if (element_size <= 0) {
        _rt_panic("rt_array_element: invalid element size");
    }
    if (index < 0) {
        _rt_panic("rt_array_element: negative index");
    }

    /* Check for overflow in multiplication */
    if ((uint64_t)index * (uint64_t)element_size > SIZE_MAX) {
        _rt_panic_fmt("rt_array_element: index * element_size overflow (%d * %d)",
                     (int)index, (int)element_size);
    }

    size_t offset = (size_t)index * (size_t)element_size;
    return (void *)((uintptr_t)array_data + offset);
}

/* =========================================================================
 * End of UNSAFE ZONE
 * ========================================================================= */

/* =========================================================================
 * Runtime support for `new` & `drop`
 * ========================================================================= */

/**
 * Internal allocation tracker for `new` / `drop`.
 *
 * Uses an open-addressing hash table of `void*` pointers for O(1) amortized
 * insert/lookup/remove.  The goal is to make misuse of `drop` (double-free /
 * invalid pointer) a defined runtime panic instead of C undefined behavior.
 */

/** Sentinel value for a deleted slot (tombstone). */
#define _RT_ALLOC_TOMBSTONE ((void*)(uintptr_t)1)

/** Initial hash-table capacity (must be a power of two). */
#define _RT_ALLOC_INIT_CAP 256

static void  **_rt_alloc_table     = NULL;
static size_t  _rt_alloc_table_cap = 0;
static size_t  _rt_alloc_table_cnt = 0; /* live (non-tombstone) entries */

/**
 * Hash a pointer value to a table index (self-contained MurmurHash3 fmix).
 */
static inline size_t _rt_alloc_hash(void *ptr, size_t cap) {
    uint64_t v = (uint64_t)(uintptr_t)ptr;
    uint32_t x = (uint32_t)(v ^ (v >> 32));
    x ^= x >> 16; x *= 0x85ebca6bu;
    x ^= x >> 13; x *= 0xc2b2ae35u;
    x ^= x >> 16;
    return (size_t)(x & (uint32_t)(cap - 1));
}

/**
 * Grow the allocation hash table by 2x and re-insert all live entries.
 */
static void _rt_alloc_table_grow(void) {
    size_t old_cap = _rt_alloc_table_cap;
    void **old_tbl = _rt_alloc_table;
    size_t new_cap = old_cap == 0 ? _RT_ALLOC_INIT_CAP : old_cap * 2;

    void **new_tbl = (void**)calloc(new_cap, sizeof(void*));
    if (new_tbl == NULL) {
        _rt_panic("new: out of memory (alloc tracker grow)");
    }

    /* Re-insert live entries (skip NULL and TOMBSTONE). */
    for (size_t i = 0; i < old_cap; i++) {
        void *p = old_tbl[i];
        if (p != NULL && p != _RT_ALLOC_TOMBSTONE) {
            size_t idx = _rt_alloc_hash(p, new_cap);
            while (new_tbl[idx] != NULL) {
                idx = (idx + 1) & (new_cap - 1);
            }
            new_tbl[idx] = p;
        }
    }

    free(old_tbl);
    _rt_alloc_table     = new_tbl;
    _rt_alloc_table_cap = new_cap;
}

/**
 * Insert a pointer into the allocation hash table.
 */
static void _rt_alloc_table_insert(void *ptr) {
    /* Grow if load factor exceeds ~70%. */
    if (_rt_alloc_table_cap == 0 ||
        (_rt_alloc_table_cnt + 1) * 10 > _rt_alloc_table_cap * 7) {
        _rt_alloc_table_grow();
    }

    size_t idx = _rt_alloc_hash(ptr, _rt_alloc_table_cap);
    while (_rt_alloc_table[idx] != NULL &&
           _rt_alloc_table[idx] != _RT_ALLOC_TOMBSTONE) {
        idx = (idx + 1) & (_rt_alloc_table_cap - 1);
    }
    _rt_alloc_table[idx] = ptr;
    _rt_alloc_table_cnt++;
}

/**
 * Remove a pointer from the allocation hash table.
 *
 * @return 1 if found and removed, 0 if not found.
 */
static int _rt_alloc_table_remove(void *ptr) {
    if (_rt_alloc_table_cap == 0) return 0;

    size_t idx = _rt_alloc_hash(ptr, _rt_alloc_table_cap);
    while (_rt_alloc_table[idx] != NULL) {
        if (_rt_alloc_table[idx] == ptr) {
            _rt_alloc_table[idx] = _RT_ALLOC_TOMBSTONE;
            _rt_alloc_table_cnt--;
            return 1;
        }
        idx = (idx + 1) & (_rt_alloc_table_cap - 1);
    }
    return 0;
}

/**
 * Allocate a single zero-initialized object for L0 `new`.
 * Panics on failure, and registers the returned pointer for `_rt_drop`.
 * 
 * @param bytes Allocation size.
 * @return Pointer to allocated object.
 */
#ifdef DEA_TRACE_MEMORY
static void *_rt_alloc_obj_impl(dea_int bytes, const char *_loc_file, int _loc_line) {
    if (bytes <= 0) {
        _rt_panic("new: invalid allocation size");
    }

    void *ptr = _rt_calloc_impl(1, bytes, _loc_file, _loc_line);
    if (ptr == NULL) {
        _rt_free_impl(ptr, _loc_file, _loc_line);
        _RT_TRACE_MEM("op=new_alloc bytes=%d ptr=%p action=panic-oom loc=\"%s\":%d", (int)bytes, ptr, _loc_file, _loc_line);
        _rt_panic("new: out of memory");
    }

    _rt_alloc_table_insert(ptr);

    _RT_TRACE_MEM("op=new_alloc bytes=%d ptr=%p action=ok loc=\"%s\":%d", (int)bytes, ptr, _loc_file, _loc_line);
    return ptr;
}
#define _rt_alloc_obj(bytes) _rt_alloc_obj_impl((bytes), __FILE__, __LINE__)
#else
static void *_rt_alloc_obj(dea_int bytes) {
    if (bytes <= 0) {
        _rt_panic("new: invalid allocation size");
    }

    void *ptr = rt_calloc(1, bytes);
    if (ptr == NULL) {
        rt_free(ptr);
        _RT_TRACE_MEM("op=new_alloc bytes=%d ptr=%p action=panic-oom", (int)bytes, ptr);
        _rt_panic("new: out of memory");
    }

    _rt_alloc_table_insert(ptr);

    _RT_TRACE_MEM("op=new_alloc bytes=%d ptr=%p action=ok", (int)bytes, ptr);
    return ptr;
}
#endif

/**
 * Drop a heap-allocated object created by `new`.
 * Frees the memory and unregisters it from the allocation tracker.
 * A NULL pointer is a no-op.
 * Panics on invalid pointers (not previously allocated by `new`).
 * 
 * @param ptr Pointer to drop.
 */
#ifdef DEA_TRACE_MEMORY
static void _rt_drop_impl(void *ptr, const char *_loc_file, int _loc_line) {
    if (ptr == NULL) {
        _RT_TRACE_MEM("op=drop ptr=%p action=noop-null loc=\"%s\":%d", ptr, _loc_file, _loc_line);
        return; /* covers drop of null optional pointers (T*?) */
    }

    if (!_rt_alloc_table_remove(ptr)) {
        _RT_TRACE_MEM("op=drop ptr=%p action=panic-not-found loc=\"%s\":%d", ptr, _loc_file, _loc_line);
        _rt_panic("drop: pointer not allocated by 'new'");
    }

    _RT_TRACE_MEM("op=drop ptr=%p action=free loc=\"%s\":%d", ptr, _loc_file, _loc_line);
    _rt_free_impl(ptr, _loc_file, _loc_line);
}
#define _rt_drop(ptr) _rt_drop_impl((ptr), __FILE__, __LINE__)
#else
static void _rt_drop(void *ptr) {
    if (ptr == NULL) {
        _RT_TRACE_MEM("op=drop ptr=%p action=noop-null", ptr);
        return; /* covers drop of null optional pointers (T*?) */
    }

    if (!_rt_alloc_table_remove(ptr)) {
        _RT_TRACE_MEM("op=drop ptr=%p action=panic-not-found", ptr);
        _rt_panic("drop: pointer not allocated by 'new'");
    }

    _RT_TRACE_MEM("op=drop ptr=%p action=free", ptr);
    free(ptr);
}
#endif

/* =========================================================================
 * Runtime support for hashing (using SipHash-1-3)
 * ========================================================================= */

/**
 * Final mixing function for 32-bit hashes (MurmurHash3 fmix32).
 * 
 * @param x Current hash.
 * @return Mixed hash.
 */
static inline uint32_t _rt_fmix32(uint32_t x) {
    x ^= x >> 16;
    x *= 0x85ebca6bu;
    x ^= x >> 13;
    x *= 0xc2b2ae35u;
    x ^= x >> 16;
    return x;
}

/**
 * Fold a 64-bit hash into a 32-bit hash with final mixing.
 * 
 * @param h 64-bit hash.
 * @return 32-bit hash.
 */
static inline uint32_t _rt_fold_u64_to_u32_fmix(uint64_t h) {
    uint32_t x = (uint32_t)(h ^ (h >> 32));
    return _rt_fmix32(x);
}

typedef uint8_t _rt_siphash_key_t[16];
typedef uint8_t _rt_siphash_tag8_t[8];

/* Type tags for L0 runtime type identification */
static const _rt_siphash_tag8_t _dea_sh_tag_bool   = { 0, 'b', 'o', 'o', 'l' };
static const _rt_siphash_tag8_t _dea_sh_tag_byte   = { 0, 'i', 'n', 't', 8 };
static const _rt_siphash_tag8_t _dea_sh_tag_int    = { 0, 'i', 'n', 't', 32 };
static const _rt_siphash_tag8_t _dea_sh_tag_string = { 0, 's', 't', 'r', 'i', 'n', 'g' };
static const _rt_siphash_tag8_t _dea_sh_tag_data   = { 0, 'd', 'a', 't', 'a' };

/* Flag bits for hash functions */
#define _DEA_TAG_OPT 0x80    /* option */
#define _DEA_TAG_PTR 0x40    /* pointer */
#define _DEA_TAG_ENUM 0x20   /* enum */
#define _DEA_TAG_STRUCT 0x10 /* struct */

/**
 * Default (debug) SipHash key for L0 runtime.
 * In production, it will be randomized at runtime to prevent hash-flooding attacks.
 */
static _rt_siphash_key_t _rt_sh_key = {
    0x00, 0x01, 0x02, 0x03, 0x04, 0x05, 0x06, 0x07,
    0x08, 0x09, 0x0A, 0x0B, 0x0C, 0x0D, 0x0E, 0x0F
};

/**
 * Internal helper to hash data with a given 8-byte tag and flags.
 * 
 * @param tag8 8-byte tag.
 * @param flags Flags.
 * @param data Pointer to data.
 * @param len Data length.
 * @param key SipHash key.
 * @return 32-bit hash.
 */
static dea_int _rt_hash_tag8(const _rt_siphash_tag8_t tag8,
                            const uint8_t flags,
                            const void *data, size_t len,
                            const _rt_siphash_key_t key)
{
    uint64_t hash = siphash13_tag8_bf(tag8, flags, data, len, key); /* compute SipHash-1-3 */
    return _rt_fold_u64_to_u32_fmix(hash);
}

/* Hash functions for basic types */

/**
 * Hash a boolean value with the runtime bool tag.
 *
 * @param value Boolean value to hash.
 * @param flags Type-shaping flags mixed into the hash domain.
 * @return 32-bit hash.
 */
static dea_int _rt_hash_bool(dea_bool value, const uint8_t flags) {
    return _rt_hash_tag8(_dea_sh_tag_bool, flags, &value, sizeof(dea_bool), _rt_sh_key);
}

/**
 * Hash a byte value with the runtime byte tag.
 *
 * @param value Byte value to hash.
 * @param flags Type-shaping flags mixed into the hash domain.
 * @return 32-bit hash.
 */
static dea_int _rt_hash_byte(dea_byte value, const uint8_t flags) {
    return _rt_hash_tag8(_dea_sh_tag_byte, flags, &value, sizeof(dea_byte), _rt_sh_key);
}

/**
 * Hash an integer value with the runtime int tag.
 *
 * @param value Integer value to hash.
 * @param flags Type-shaping flags mixed into the hash domain.
 * @return 32-bit hash.
 */
static dea_int _rt_hash_int(dea_int value, const uint8_t flags) {
    return _rt_hash_tag8(_dea_sh_tag_int, flags, &value, sizeof(dea_int), _rt_sh_key);
}

/**
 * Hash a string's byte contents with the runtime string tag.
 *
 * @param str String value to hash.
 * @param flags Type-shaping flags mixed into the hash domain.
 * @return 32-bit hash.
 */
static dea_int _rt_hash_string(dea_string str, const uint8_t flags) {
    const char *str_data = _rt_string_bytes(str);
    dea_int str_len = rt_strlen(str);
    return _rt_hash_tag8(_dea_sh_tag_string, flags, str_data, (size_t)str_len, _rt_sh_key);
}

/**
 * Hash an arbitrary byte sequence with the runtime data tag.
 *
 * @param data Pointer to the byte sequence.
 * @param size Size of `data` in bytes.
 * @param flags Type-shaping flags mixed into the hash domain.
 * @return 32-bit hash.
 */
static dea_int _rt_hash_data(void *data, dea_int size, const uint8_t flags) {
    return _rt_hash_tag8(_dea_sh_tag_data, flags, data, (size_t)size, _rt_sh_key);
}

/* =========================================================================
 * User-exposed hash functions
 * ========================================================================= */

/**
 * Hash a boolean value.
 * 
 * @param value Boolean value.
 * @return 32-bit hash.
 *
 * L0 signature: `extern func rt_hash_bool(value: bool) -> int;` 
 */
static dea_int rt_hash_bool(dea_bool value) {
    return _rt_hash_bool(value, 0);
}

/**
 * Hash a byte value.
 * 
 * @param value Byte value.
 * @return 32-bit hash.
 *
 * L0 signature: `extern func rt_hash_byte(value: byte) -> int;` 
 */
static dea_int rt_hash_byte(dea_byte value) {
    return _rt_hash_byte(value, 0);
}

/**
 * Hash an integer value.
 * 
 * @param value Integer value.
 * @return 32-bit hash.
 *
 * L0 signature: `extern func rt_hash_int(value: int) -> int;` 
 */
static dea_int rt_hash_int(dea_int value) {
    return _rt_hash_int(value, 0);
}

/**
 * Hash a string value.
 * 
 * @param value L0 string.
 * @return 32-bit hash.
 *
 * L0 signature: `extern func rt_hash_string(value: string) -> int;` 
 */
static dea_int rt_hash_string(dea_string value) {
    return _rt_hash_string(value, 0);
}

/**
 * Hash raw data.
 * Panics if data is null or size is negative.
 * 
 * @param data Pointer to data.
 * @param size Data size.
 * @return 32-bit hash.
 *
 * L0 signature: `extern func rt_hash_data(data: void*, size: int) -> int;` 
 */
static dea_int rt_hash_data(void *data, dea_int size) {
    if (size < 0) {
        _rt_panic("rt_hash_data: negative size");
    }
    if (data == NULL) {
        _rt_panic("rt_hash_data: null data pointer");
    }
    return _rt_hash_data(data, size, 0);
}

/**
 * Hash an optional boolean value.
 * 
 * @param opt Optional bool.
 * @return 32-bit hash.
 *
 * L0 signature: `extern func rt_hash_opt_bool(opt: bool?) -> int;` 
 */
static dea_int rt_hash_opt_bool(dea_opt_bool opt) {
    uint8_t flags = _DEA_TAG_OPT;
    return _rt_hash_data(&opt, sizeof(dea_opt_bool), flags);
}

/**
 * Hash an optional byte value.
 * 
 * @param opt Optional byte.
 * @return 32-bit hash.
 *
 * L0 signature: `extern func rt_hash_opt_byte(opt: byte?) -> int;` 
 */
static dea_int rt_hash_opt_byte(dea_opt_byte opt) {
    uint8_t flags = _DEA_TAG_OPT;
    return _rt_hash_data(&opt, sizeof(dea_opt_byte), flags);
}

/**
 * Hash an optional integer value.
 * 
 * @param opt Optional int.
 * @return 32-bit hash.
 *
 * L0 signature: `extern func rt_hash_opt_int(opt: int?) -> int;` 
 */
static dea_int rt_hash_opt_int(dea_opt_int opt) {
    uint8_t flags = _DEA_TAG_OPT;
    return _rt_hash_data(&opt, sizeof(dea_opt_int), flags);
}

/**
 * Hash an optional string value.
 * If opt is empty, hashes as an empty string with the optional flag.
 * 
 * @param opt Optional string.
 * @return 32-bit hash.
 *
 * L0 signature: `extern func rt_hash_opt_string(opt: string?) -> int;` 
 */
static dea_int rt_hash_opt_string(dea_opt_string opt) {
    uint8_t flags = _DEA_TAG_OPT;
    if (opt.has_value) {
        return _rt_hash_string(opt.value, flags);
    } else {
        return _rt_hash_string(DEA_STRING_EMPTY, flags);
    }
}

/**
 * Hash a pointer value.
 * Note: this hashes the pointer value (address), not the data it points to.
 * Panics if ptr is null.
 * 
 * @param ptr Pointer.
 * @return 32-bit hash.
 *
 * L0 signature: `extern func rt_hash_ptr(ptr: void*) -> int;` 
 */
static dea_int rt_hash_ptr(void *ptr) {
    if (ptr == NULL) {
        _rt_panic("rt_hash_ptr: null pointer");
    }
    uint8_t flags = _DEA_TAG_PTR;
    return _rt_hash_data(&ptr, sizeof(void*), flags);
}

/**
 * Hash an optional pointer value.
 * Note: this hashes the pointer value (address), not the data it points to.
 * Panics if opt is empty (null pointer).
 * 
 * @param opt Pointer.
 * @return 32-bit hash.
 *
 * L0 signature: `extern func rt_hash_opt_ptr(opt: void*?) -> int;` 
 */
static dea_int rt_hash_opt_ptr(void *opt) {
    if (opt == NULL) {
        _rt_panic("rt_hash_opt_ptr: unwrap of empty optional");
    }
    uint8_t flags = _DEA_TAG_OPT | _DEA_TAG_PTR;
    return _rt_hash_data(&opt, sizeof(void*), flags);
}

/* =========================================================================
 * Optional real-number helpers
 * ========================================================================= */

#ifdef DEA_USE_SYS_REAL
#include "l1_real.h"
#endif

/* =========================================================================
 * End of L1 Runtime
 * ========================================================================= */

#endif /* L1_RUNTIME_H */
