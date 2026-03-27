#!/bin/bash
#
# SPDX-License-Identifier: MIT OR Apache-2.0
# Copyright (c) 2026 gwz
#

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/../../.." && pwd)"
MONOREPO_ROOT="$(cd "$REPO_ROOT/.." && pwd)"
BUILD_TESTS_ROOT="$REPO_ROOT/build/tests"
PREFIX_DIR="$(mktemp -d /tmp/scratch.XXXXXX)"
DIST_DIR_PATH=""
TRACE_LOG="/tmp/l0_stage2_test_env_isolation_$$.log"

cleanup() {
    rm -rf "$PREFIX_DIR"
    if [ -n "$DIST_DIR_PATH" ]; then
        rm -rf "$DIST_DIR_PATH"
    fi
    rm -f "$TRACE_LOG"
}
trap cleanup EXIT

fail() {
    echo "l0c_stage2_test_env_isolation_test: FAIL: $1" >&2
    exit 1
}

assert_contains() {
    local path="$1"
    local needle="$2"
    grep -F "$needle" "$path" >/dev/null || fail "expected '$needle' in $path"
}

assert_not_contains() {
    local path="$1"
    local needle="$2"
    if grep -F "$needle" "$path" >/dev/null; then
        fail "did not expect '$needle' in $path"
    fi
}

resolve_repo_python() {
    if [ -x "$MONOREPO_ROOT/.venv/bin/python" ]; then
        printf '%s\n' "$MONOREPO_ROOT/.venv/bin/python"
        return 0
    fi
    if [ -x "$MONOREPO_ROOT/.venv/Scripts/python.exe" ]; then
        printf '%s\n' "$MONOREPO_ROOT/.venv/Scripts/python.exe"
        return 0
    fi
    fail "missing repo virtualenv python"
}

cd "$REPO_ROOT"
mkdir -p "$BUILD_TESTS_ROOT"
DIST_DIR_PATH="$(mktemp -d "$BUILD_TESTS_ROOT/l0_stage2_envdist.XXXXXX")"
DIST_DIR_REL="${DIST_DIR_PATH#$REPO_ROOT/}"

make venv DEA_BUILD_DIR="$DIST_DIR_REL" install-dev-stage2 >/dev/null
make PREFIX="$PREFIX_DIR" install >/dev/null

REPO_PYTHON="$(resolve_repo_python)"
if ! bash -lc 'source "$1/bin/l0-env.sh" && DEA_BUILD_DIR="$2" "$3" ./compiler/stage2_l0/run_test_trace.py parser_test' bash "$PREFIX_DIR" "$DIST_DIR_REL" "$REPO_PYTHON" >"$TRACE_LOG" 2>&1; then
    cat "$TRACE_LOG" >&2
    fail "run_test_trace.py failed after sourcing the installed prefix env"
fi

assert_contains "$TRACE_LOG" "exit_code=0"
assert_not_contains "$TRACE_LOG" "$PREFIX_DIR/stage1_py/l0c.py"

echo "l0c_stage2_test_env_isolation_test: PASS"
