#!/bin/bash
#
# SPDX-License-Identifier: MIT OR Apache-2.0
# Copyright (c) 2026 gwz
#
# End-to-end regression for Stage 2 `--ast` mode.
#
# Verifies:
#   - single-module --ast succeeds and produces expected output
#   - --ast --all-modules succeeds for a multi-module fixture
#   - --all-modules module headers appear in sorted order
#   - L0C-9510 ("not implemented") is absent from successful --ast output
#   - a bad target name produces a failure diagnostic rather than L0C-9510

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/../../.." && pwd)"
FIXTURE_ROOT="$REPO_ROOT/compiler/stage2_l0/tests/fixtures/driver"
mkdir -p "$REPO_ROOT/build"
TMP_DIR="$(mktemp -d "$REPO_ROOT/build/l0c-stage2-ast-test.XXXXXX")"
DEA_BUILD_DIR="$TMP_DIR/dea"

is_windows_host() {
    case "$(uname -s)" in
        CYGWIN*|MINGW*|MSYS*) return 0 ;;
    esac
    return 1
}

native_path() {
    local path="$1"
    if is_windows_host; then
        cygpath -w "$path"
    else
        printf '%s\n' "$path"
    fi
}

stage2_launcher_path() {
    local base="$1"
    if is_windows_host && [ -f "$base.cmd" ]; then
        native_path "$base.cmd"
    else
        printf '%s\n' "$base"
    fi
}

clean_env_run() {
    if is_windows_host; then
        env -i PATH="$PATH" SYSTEMROOT="${SYSTEMROOT:-}" COMSPEC="${COMSPEC:-}" WINDIR="${WINDIR:-}" OS="${OS:-}" TEMP="${TEMP:-}" TMP="${TMP:-}" "$@"
    else
        env -i PATH="$PATH" "$@"
    fi
}

cleanup() {
    rm -rf "$TMP_DIR"
}
trap cleanup EXIT

fail() {
    echo "l0c_ast_test: FAIL: $1" >&2
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

assert_empty() {
    local path="$1"
    [ ! -s "$path" ] || fail "expected empty file: $path"
}

assert_line_before() {
    local path="$1"
    local first="$2"
    local second="$3"
    local line_first line_second
    line_first=$(grep -nF "$first" "$path" | head -1 | cut -d: -f1)
    line_second=$(grep -nF "$second" "$path" | head -1 | cut -d: -f1)
    [ -n "$line_first" ] || fail "line '$first' not found in $path"
    [ -n "$line_second" ] || fail "line '$second' not found in $path"
    [ "$line_first" -lt "$line_second" ] || fail "expected '$first' before '$second' in $path"
}

cd "$REPO_ROOT"
DEA_BUILD_DIR="$DEA_BUILD_DIR" ./scripts/build-stage2-l0c.sh >/dev/null

STAGE2_L0C="$(stage2_launcher_path "$DEA_BUILD_DIR/bin/l0c-stage2")"
FIXTURE_ROOT_NATIVE="$(native_path "$FIXTURE_ROOT")"

# --- 1. Single-module --ast succeeds ---

AST_STDOUT="$TMP_DIR/ast.stdout"
AST_STDERR="$TMP_DIR/ast.stderr"
if ! clean_env_run "$STAGE2_L0C" --ast -P "$FIXTURE_ROOT_NATIVE" ok_leaf \
        >"$AST_STDOUT" 2>"$AST_STDERR"; then
    fail "--ast ok_leaf should succeed"
fi

assert_not_contains "$AST_STDOUT" "L0C-9510"
assert_contains "$AST_STDOUT" "Module(name='ok_leaf'"
assert_contains "$AST_STDOUT" "FuncDecl("
assert_contains "$AST_STDOUT" "ReturnStmt("

# --- 2. --ast --all-modules succeeds for a multi-module fixture ---

ALL_STDOUT="$TMP_DIR/all.stdout"
ALL_STDERR="$TMP_DIR/all.stderr"
if ! clean_env_run "$STAGE2_L0C" --ast --all-modules -P "$FIXTURE_ROOT_NATIVE" ok_main \
        >"$ALL_STDOUT" 2>"$ALL_STDERR"; then
    fail "--ast --all-modules ok_main should succeed"
fi

assert_not_contains "$ALL_STDOUT" "L0C-9510"

# Each loaded module must appear with its header
assert_contains "$ALL_STDOUT" "=== Module ok_dep1 ==="
assert_contains "$ALL_STDOUT" "=== Module ok_dep2 ==="
assert_contains "$ALL_STDOUT" "=== Module ok_leaf ==="
assert_contains "$ALL_STDOUT" "=== Module ok_main ==="

# Each module's AST header must appear
assert_contains "$ALL_STDOUT" "Module(name='ok_main'"
assert_contains "$ALL_STDOUT" "Module(name='ok_dep1'"
assert_contains "$ALL_STDOUT" "Module(name='ok_dep2'"
assert_contains "$ALL_STDOUT" "Module(name='ok_leaf'"

# --- 3. Module headers appear in sorted (alphabetical) order ---

assert_line_before "$ALL_STDOUT" "=== Module ok_dep1 ===" "=== Module ok_dep2 ==="
assert_line_before "$ALL_STDOUT" "=== Module ok_dep2 ===" "=== Module ok_leaf ==="
assert_line_before "$ALL_STDOUT" "=== Module ok_leaf ===" "=== Module ok_main ==="

# --- 4. L0C-9510 must not appear in any successful --ast output ---

assert_not_contains "$AST_STDOUT" "L0C-9510"
assert_not_contains "$ALL_STDOUT" "L0C-9510"

# --- 5. Bad target produces a diagnostic, not L0C-9510 ---

BAD_STDOUT="$TMP_DIR/bad.stdout"
BAD_STDERR="$TMP_DIR/bad.stderr"
set +e
clean_env_run "$STAGE2_L0C" --ast -P "$FIXTURE_ROOT_NATIVE" no_such_module_xyz \
        >"$BAD_STDOUT" 2>"$BAD_STDERR"
BAD_RC=$?
set -e

[ "$BAD_RC" -ne 0 ] || fail "bad target should fail"
assert_not_contains "$BAD_STDERR" "L0C-9510"

# stderr must contain an error diagnostic; stdout must be empty
assert_empty "$BAD_STDOUT"
grep -E '\[.*\]' "$BAD_STDERR" >/dev/null || fail "expected a diagnostic code in stderr for bad target"

# --- 6. --ast on the examples/hello fixture succeeds (uses installed stdlib) ---

HELLO_STDOUT="$TMP_DIR/hello.stdout"
HELLO_STDERR="$TMP_DIR/hello.stderr"
if ! clean_env_run "$STAGE2_L0C" --ast -P "$(native_path "$REPO_ROOT/examples")" hello \
        >"$HELLO_STDOUT" 2>"$HELLO_STDERR"; then
    fail "--ast examples/hello should succeed"
fi

assert_contains "$HELLO_STDOUT" "Module(name='hello'"
assert_not_contains "$HELLO_STDOUT" "L0C-9510"

echo "l0c_ast_test: PASS"
