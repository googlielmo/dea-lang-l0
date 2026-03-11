#!/bin/bash
#
# SPDX-License-Identifier: MIT OR Apache-2.0
# Copyright (c) 2026 gwz
#

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/../../.." && pwd)"
BOOTSTRAP_PARENT="$REPO_ROOT/build/tests"
BOOTSTRAP_DIR=""
ALT_DIST=""
PROBE_ROOT=""
OUTSIDE_DIST="$(mktemp -d /tmp/l0_stage2_outside_dist.XXXXXX)"

# This is the full end-to-end regression for one Stage 2 compiler artifact built
# into an isolated repo-local test dist under `build/tests/...`.
#
# It validates:
# - the normal artifact shape (`l0c-stage2`, `l0c-stage2.native`, no retained C
#   by default),
# - direct wrapper usage for `--check`, `--gen`, `--build`, and `--run`,
# - retained-C behavior with `KEEP_C=1`,
# - rejection of invalid `DIST_DIR` values (outside-repo and repo-root).
#
# This test intentionally does not exercise the builder's default no-`DIST_DIR`
# destination under `build/stage2`; that narrower contract is covered separately
# by `l0c_stage2_default_dist_test.sh` so `run_tests.py` / `make test-all` do
# not leave `build/stage2` behind after a normal test run.

cleanup() {
    if [ -n "$BOOTSTRAP_DIR" ]; then
        rm -rf "$BOOTSTRAP_DIR"
    fi
    if [ -n "$ALT_DIST" ]; then
        rm -rf "$ALT_DIST"
    fi
    if [ -n "$PROBE_ROOT" ]; then
        rm -rf "$PROBE_ROOT"
    fi
    rm -rf "$OUTSIDE_DIST"
}
trap cleanup EXIT

fail() {
    echo "l0c_stage2_bootstrap_test: FAIL: $1" >&2
    exit 1
}

assert_file() {
    local path="$1"
    [ -f "$path" ] || fail "expected file: $path"
}

assert_no_file() {
    local path="$1"
    [ ! -e "$path" ] || fail "did not expect path: $path"
}

assert_contains() {
    local path="$1"
    local needle="$2"
    grep -F "$needle" "$path" >/dev/null || fail "expected '$needle' in $path"
}

cd "$REPO_ROOT"
mkdir -p "$BOOTSTRAP_PARENT"
BOOTSTRAP_DIR="$(mktemp -d "$BOOTSTRAP_PARENT/l0_stage2_bootstrap.XXXXXX")"
DIST_DIR="${BOOTSTRAP_DIR#$REPO_ROOT/}" ./scripts/build-stage2-l0c.sh >/dev/null

assert_file "$BOOTSTRAP_DIR/bin/l0c-stage2"
assert_file "$BOOTSTRAP_DIR/bin/l0c-stage2.native"
assert_no_file "$BOOTSTRAP_DIR/bin/l0c-stage2.c"

env -i PATH="$PATH" "$BOOTSTRAP_DIR/bin/l0c-stage2" --check -P examples hello >/dev/null
PROBE_ROOT="$(mktemp -d "$BOOTSTRAP_PARENT/l0_stage2_probe.XXXXXX")"
cat > "$PROBE_ROOT/qualified_expr.l0" <<'EOF'
module qualified_expr;

import std.unit;

func main() -> int {
    let maybe = std.unit::present();
    if (maybe != null) {
        return 0;
    }
    return 1;
}
EOF
cat > "$PROBE_ROOT/control_flow_cond.l0" <<'EOF'
module control_flow_cond;

import std.string;

extern func rt_print_int(x: int) -> void;
extern func rt_println() -> void;

func next_value(i: int) -> string {
    if (i == 0) {
        return concat_s("x", "");
    }
    return concat_s("", "");
}

func main() -> int {
    let i: int = 0;
    while (i < 3 && len_s(next_value(i)) > 0) {
        rt_print_int(i);
        rt_println();
        i = i + 1;
    }
    rt_print_int(i);
    rt_println();
    return 0;
}
EOF
cat > "$PROBE_ROOT/logical_expr.l0" <<'EOF'
module logical_expr;

import std.string;

extern func rt_print_int(x: int) -> void;
extern func rt_println() -> void;

func tick(n: int) -> string {
    rt_print_int(n);
    rt_println();
    return concat_s("x", "");
}

func main() -> int {
    let a: bool = false && len_s(tick(7)) > 0;
    let b: bool = true || len_s(tick(8)) > 0;
    let c: bool = false || len_s(tick(9)) > 0;
    let d: bool = true && len_s(tick(10)) > 0;

    if (a) {
        rt_print_int(1);
        rt_println();
    }
    if (b && c && d) {
        rt_print_int(2);
        rt_println();
    }
    return 0;
}
EOF
env -i PATH="$PATH" "$BOOTSTRAP_DIR/bin/l0c-stage2" --check -P "$PROBE_ROOT" qualified_expr >/dev/null
env -i PATH="$PATH" "$BOOTSTRAP_DIR/bin/l0c-stage2" --run -P "$PROBE_ROOT" control_flow_cond > /tmp/l0_stage2_bootstrap_cond_$$.out
assert_contains "/tmp/l0_stage2_bootstrap_cond_$$.out" "0"
assert_contains "/tmp/l0_stage2_bootstrap_cond_$$.out" "1"
if grep -x "2" /tmp/l0_stage2_bootstrap_cond_$$.out >/dev/null; then
    fail "expected control_flow_cond loop to stop after i=1"
fi
env -i PATH="$PATH" "$BOOTSTRAP_DIR/bin/l0c-stage2" --run -P "$PROBE_ROOT" logical_expr > /tmp/l0_stage2_bootstrap_logic_$$.out
assert_contains "/tmp/l0_stage2_bootstrap_logic_$$.out" "9"
assert_contains "/tmp/l0_stage2_bootstrap_logic_$$.out" "10"
assert_contains "/tmp/l0_stage2_bootstrap_logic_$$.out" "2"
if grep -x "7" /tmp/l0_stage2_bootstrap_logic_$$.out >/dev/null; then
    fail "expected logical_expr to short-circuit false && RHS"
fi
if grep -x "8" /tmp/l0_stage2_bootstrap_logic_$$.out >/dev/null; then
    fail "expected logical_expr to short-circuit true || RHS"
fi
env -i PATH="$PATH" "$BOOTSTRAP_DIR/bin/l0c-stage2" --gen --no-line-directives -P examples hello > /tmp/l0_stage2_bootstrap_gen_$$.c
rm -f /tmp/l0_stage2_bootstrap_gen_$$.c
env -i PATH="$PATH" "$BOOTSTRAP_DIR/bin/l0c-stage2" --build --keep-c -P examples -o /tmp/l0_stage2_bootstrap_hello_$$ hello >/dev/null
assert_file "/tmp/l0_stage2_bootstrap_hello_$$"
assert_file "/tmp/l0_stage2_bootstrap_hello_$$.c"
"/tmp/l0_stage2_bootstrap_hello_$$" > /tmp/l0_stage2_bootstrap_hello_$$.out
assert_contains "/tmp/l0_stage2_bootstrap_hello_$$.out" "Hello, World!"
env -i PATH="$PATH" "$BOOTSTRAP_DIR/bin/l0c-stage2" --run -P examples hello > /tmp/l0_stage2_bootstrap_run_$$.out
assert_contains "/tmp/l0_stage2_bootstrap_run_$$.out" "Hello, World!"
rm -f /tmp/l0_stage2_bootstrap_cond_$$.out /tmp/l0_stage2_bootstrap_logic_$$.out /tmp/l0_stage2_bootstrap_hello_$$ /tmp/l0_stage2_bootstrap_hello_$$.c /tmp/l0_stage2_bootstrap_hello_$$.out /tmp/l0_stage2_bootstrap_run_$$.out

ALT_DIST="$(mktemp -d "$BOOTSTRAP_PARENT/l0_stage2_bootstrap_keepc.XXXXXX")"
DIST_DIR="${ALT_DIST#$REPO_ROOT/}" KEEP_C=1 ./scripts/build-stage2-l0c.sh >/dev/null

assert_file "$ALT_DIST/bin/l0c-stage2"
assert_file "$ALT_DIST/bin/l0c-stage2.native"
assert_file "$ALT_DIST/bin/l0c-stage2.c"

if DIST_DIR="$OUTSIDE_DIST" ./scripts/build-stage2-l0c.sh >/tmp/l0_stage2_bootstrap_outside_$$.log 2>&1; then
    rm -f /tmp/l0_stage2_bootstrap_outside_$$.log
    fail "expected outside-repo DIST_DIR rejection"
fi
rm -f /tmp/l0_stage2_bootstrap_outside_$$.log

if DIST_DIR="." ./scripts/build-stage2-l0c.sh >/tmp/l0_stage2_bootstrap_repo_root_$$.log 2>&1; then
    rm -f /tmp/l0_stage2_bootstrap_repo_root_$$.log
    fail "expected repo-root DIST_DIR rejection"
fi
rm -f /tmp/l0_stage2_bootstrap_repo_root_$$.log

echo "l0c_stage2_bootstrap_test: PASS"
