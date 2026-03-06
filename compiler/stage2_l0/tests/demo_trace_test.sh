#!/bin/bash
#
# SPDX-License-Identifier: MIT OR Apache-2.0
# Copyright (c) 2026 gwz
#

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/../../.." && pwd)"
TRACE_CHECKER="$REPO_ROOT/compiler/stage2_l0/check_trace_log.py"
TARGET="$REPO_ROOT/examples/demo.l0"
ARTIFACT_DIR="$(mktemp -d /tmp/l0_demo_trace_test.XXXXXX)"

cleanup() {
    if [ "${KEEP_ARTIFACTS:-0}" -eq 0 ]; then
        rm -rf "$ARTIFACT_DIR"
    fi
}
trap cleanup EXIT

fail() {
    echo "demo_trace_test: FAIL: $1"
    echo "demo_trace_test: artifacts=$ARTIFACT_DIR"
    KEEP_ARTIFACTS=1
    exit 1
}

assert_contains() {
    local file="$1"
    local needle="$2"
    if ! grep -F "$needle" "$file" >/dev/null 2>&1; then
        fail "expected '$needle' in $file"
    fi
}

run_case() {
    local name="$1"
    local expected_rc="$2"
    local expected_stdout_substr="$3"
    shift 3 || true

    local out="$ARTIFACT_DIR/${name}.stdout.log"
    local trace="$ARTIFACT_DIR/${name}.stderr.log"
    local report="$ARTIFACT_DIR/${name}.trace_report.txt"
    local rc
    local analyzer_rc

    if [ "$#" -gt 0 ]; then
        if ./l0c --run --trace-memory --trace-arc "$TARGET" -- "$@" >"$out" 2>"$trace"; then
            rc=0
        else
            rc=$?
        fi
    else
        if ./l0c --run --trace-memory --trace-arc "$TARGET" >"$out" 2>"$trace"; then
            rc=0
        else
            rc=$?
        fi
    fi

    if [ "$rc" -ne "$expected_rc" ]; then
        fail "$name expected exit code $expected_rc, got $rc"
    fi

    if python3 "$TRACE_CHECKER" --triage "$trace" >"$report"; then
        analyzer_rc=0
    else
        analyzer_rc=$?
    fi

    if [ "$analyzer_rc" -ne 0 ]; then
        fail "$name trace triage failed (analyzer_rc=$analyzer_rc)"
    fi

    assert_contains "$report" "errors=0"
    assert_contains "$report" "leaked_object_ptrs=0"
    assert_contains "$report" "leaked_string_ptrs=0"
    assert_contains "$out" "$expected_stdout_substr"
}

run_case "ok_mul" 0 "= 32" mul 4 add 5 3
run_case "ok_add" 0 "= 5" add 2 3
run_case "ok_mul_2" 0 "= 32" mul 4 add 5 mul 1 mul 1 3
run_case "err_unknown_op" 1 "usage: demo <expr>" foo 1 2
run_case "err_incomplete_rhs" 1 "usage: demo <expr>" add 1
run_case "err_no_args" 1 "usage: demo <expr>"
run_case "err_trailing_token" 1 "usage: demo <expr>" add 1 2 3

echo "demo_trace_test: PASS"
