#!/bin/bash
#
# SPDX-License-Identifier: MIT OR Apache-2.0
# Copyright (c) 2026 gwz
#

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/../../.." && pwd)"
FIXTURE_ROOT="$REPO_ROOT/compiler/stage2_l0/tests/fixtures/driver"
TMP_DIR="$(mktemp -d "$REPO_ROOT/build/l0c-stage2-verbose-test.XXXXXX")"
DEA_BUILD_DIR="$TMP_DIR/dea"

cleanup() {
    rm -rf "$TMP_DIR"
}
trap cleanup EXIT

fail() {
    echo "l0c_stage2_verbose_output_test: FAIL: $1" >&2
    exit 1
}

assert_contains() {
    local path="$1"
    local text="$2"
    grep -F "$text" "$path" >/dev/null || fail "expected '$text' in $path"
}

assert_not_contains() {
    local path="$1"
    local text="$2"
    if grep -F "$text" "$path" >/dev/null; then
        fail "did not expect '$text' in $path"
    fi
}

assert_matches() {
    local path="$1"
    local pattern="$2"
    grep -E "$pattern" "$path" >/dev/null || fail "expected pattern '$pattern' in $path"
}

assert_empty() {
    local path="$1"
    [ ! -s "$path" ] || fail "expected empty file: $path"
}

cd "$REPO_ROOT"
mkdir -p "$REPO_ROOT/build"
DEA_BUILD_DIR="$DEA_BUILD_DIR" ./scripts/build-stage2-l0c.sh >/dev/null

STAGE2_L0C="$DEA_BUILD_DIR/bin/l0c-stage2"

V_STDOUT="$TMP_DIR/v.stdout"
V_STDERR="$TMP_DIR/v.stderr"
if ! env -i PATH="$PATH" "$STAGE2_L0C" -v --build -P "$FIXTURE_ROOT" ok_main >"$V_STDOUT" 2>"$V_STDERR"; then
    fail "-v --build should succeed"
fi

assert_empty "$V_STDOUT"
assert_contains "$V_STDERR" "Dea language / L0 compiler (Stage 2)"
assert_contains "$V_STDERR" "System root(s): '$REPO_ROOT/compiler/shared/l0/stdlib'"
assert_contains "$V_STDERR" "Project root(s): '$FIXTURE_ROOT'"
assert_contains "$V_STDERR" "Starting analysis for entry module 'ok_main'"
assert_contains "$V_STDERR" "Building compilation unit module 'ok_main'"
assert_contains "$V_STDERR" "Resolving module-level names..."
assert_contains "$V_STDERR" "Resolving type signatures..."
assert_contains "$V_STDERR" "Resolving local scopes..."
assert_contains "$V_STDERR" "Type-checking expressions..."
assert_contains "$V_STDERR" "Analysis complete: 0 total diagnostic(s), 0 error(s)"
assert_contains "$V_STDERR" "Generating C code..."
assert_contains "$V_STDERR" "Generated C code: "
assert_contains "$V_STDERR" "Using C compiler: "
assert_contains "$V_STDERR" "Detected compiler flag family: "
assert_contains "$V_STDERR" "Adding optimization flag: "
assert_contains "$V_STDERR" "Compiling:"
assert_matches "$V_STDERR" " -o a\\.out"
assert_contains "$V_STDERR" "Built executable: a.out"
assert_not_contains "$V_STDERR" "Loading module 'ok_main'"
assert_not_contains "$V_STDERR" "Preparing optional wrapper types"
assert_not_contains "$V_STDERR" "already loaded (cache hit)"

VVV_STDOUT="$TMP_DIR/vvv.stdout"
VVV_STDERR="$TMP_DIR/vvv.stderr"
if ! env -i PATH="$PATH" "$STAGE2_L0C" -vvv --build -P "$FIXTURE_ROOT" ok_main >"$VVV_STDOUT" 2>"$VVV_STDERR"; then
    fail "-vvv --build should succeed"
fi

assert_empty "$VVV_STDOUT"
assert_contains "$VVV_STDERR" "Loading module 'ok_main'"
assert_contains "$VVV_STDERR" "Resolved 'ok_main' to $FIXTURE_ROOT/ok_main.l0"
assert_contains "$VVV_STDERR" "Lexing $FIXTURE_ROOT/ok_main.l0"
assert_contains "$VVV_STDERR" "Lexed 21 token(s) from $FIXTURE_ROOT/ok_main.l0"
assert_contains "$VVV_STDERR" "Parsing $FIXTURE_ROOT/ok_main.l0"
assert_contains "$VVV_STDERR" "Parsed module 'ok_main' from $FIXTURE_ROOT/ok_main.l0"
assert_contains "$VVV_STDERR" "Loading module 'ok_dep1'"
assert_contains "$VVV_STDERR" "Lexed 18 token(s) from $FIXTURE_ROOT/ok_dep1.l0"
assert_contains "$VVV_STDERR" "Loading module 'ok_leaf'"
assert_contains "$VVV_STDERR" "Lexed 15 token(s) from $FIXTURE_ROOT/ok_leaf.l0"
assert_contains "$VVV_STDERR" "Loading module 'ok_dep2'"
assert_contains "$VVV_STDERR" "Lexed 15 token(s) from $FIXTURE_ROOT/ok_dep2.l0"
assert_contains "$VVV_STDERR" "Module 'ok_dep1' already loaded (cache hit)"
assert_contains "$VVV_STDERR" "Module 'ok_leaf' already loaded (cache hit)"
assert_contains "$VVV_STDERR" "Module 'ok_dep2' already loaded (cache hit)"
assert_contains "$VVV_STDERR" "Compilation unit contains 4 module(s): ok_dep1, ok_dep2, ok_leaf, ok_main"
assert_contains "$VVV_STDERR" "Name resolution produced 0 diagnostic(s)"
assert_contains "$VVV_STDERR" "Signature resolution found 4 function(s), 0 struct(s), 0 enum(s), 0 let(s)"
assert_contains "$VVV_STDERR" "Local scope resolution processed 4 function(s)"
assert_contains "$VVV_STDERR" "Expression type checking produced 0 diagnostic(s)"
assert_contains "$VVV_STDERR" "Preparing optional wrapper types"
assert_contains "$VVV_STDERR" "Emitting header and forward declarations"
assert_not_contains "$VVV_STDERR" "Generating module 'ok_main'"
assert_not_contains "$VVV_STDERR" "already loaded (cached)"

PATH_STDOUT="$TMP_DIR/path.stdout"
PATH_STDERR="$TMP_DIR/path.stderr"
if ! env -i PATH="$PATH" "$STAGE2_L0C" -vvv examples/demo.l0 >"$PATH_STDOUT" 2>"$PATH_STDERR"; then
    fail "-vvv examples/demo.l0 should succeed"
fi

assert_empty "$PATH_STDOUT"
assert_contains "$PATH_STDERR" "Project root(s): 'examples'"
assert_not_contains "$PATH_STDERR" "Project root(s): '.','examples'"

RUN_STDOUT="$TMP_DIR/run.stdout"
RUN_STDERR="$TMP_DIR/run.stderr"
if ! env -i PATH="$PATH" "$STAGE2_L0C" -v --run -P "$FIXTURE_ROOT" ok_main >"$RUN_STDOUT" 2>"$RUN_STDERR"; then
    fail "-v --run should succeed"
fi

assert_empty "$RUN_STDOUT"
assert_contains "$RUN_STDERR" "Running: "

echo "l0c_stage2_verbose_output_test: PASS"
