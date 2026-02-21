#!/bin/bash
#
# SPDX-License-Identifier: MIT OR Apache-2.0
# Copyright (c) 2026 gwz
#

set -euo pipefail

VERBOSE=0
KEEP_ARTIFACTS=0
MAX_DETAILS=5

usage() {
    echo "Usage: $0 [-v] [--keep-artifacts] [--max-details <n>]"
    echo "  -v                 Show trace analyzer report for each test."
    echo "  --keep-artifacts   Keep trace/stdout/report files under the temp directory."
    echo "  --max-details <n>  Passed to check_trace_log.py (default: 5)."
}

while [ $# -gt 0 ]; do
    case "$1" in
        -v)
            VERBOSE=1
            shift
            ;;
        --keep-artifacts)
            KEEP_ARTIFACTS=1
            shift
            ;;
        --max-details)
            if [ $# -lt 2 ]; then
                usage
                exit 2
            fi
            MAX_DETAILS="$2"
            shift 2
            ;;
        -h|--help)
            usage
            exit 0
            ;;
        *)
            echo "Unknown argument: $1"
            usage
            exit 2
            ;;
    esac
done

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"
TESTS_DIR="$SCRIPT_DIR/tests"
TRACE_CHECKER="$SCRIPT_DIR/check_trace_log.py"
ARTIFACT_DIR="$(mktemp -d /tmp/l0_stage2_trace_tests.XXXXXX)"

cleanup() {
    if [ "$KEEP_ARTIFACTS" -eq 0 ]; then
        rm -rf "$ARTIFACT_DIR"
    fi
}
trap cleanup EXIT

cd "$REPO_ROOT"

passed=0
failed=0
failed_tests=""

echo "Running stage2_l0 trace checks..."
echo "artifacts=$ARTIFACT_DIR"
echo "======================================"

for test_file in "$TESTS_DIR"/*.l0; do
    test_name=$(basename "$test_file" .l0)
    out="$ARTIFACT_DIR/${test_name}.stdout.log"
    trace="$ARTIFACT_DIR/${test_name}.stderr.log"
    report="$ARTIFACT_DIR/${test_name}.trace_report.txt"

    if ./l0c --trace-memory --trace-arc -P compiler/stage2_l0/src --run "$test_file" >"$out" 2>"$trace"; then
        if python3 "$TRACE_CHECKER" "$trace" --triage --max-details "$MAX_DETAILS" >"$report"; then
            leaks=$(grep -E "leaked_object_ptrs=|leaked_string_ptrs=" "$report" | tr '\n' ' ')
            echo "$test_name: TRACE_OK $leaks"
            if [ "$VERBOSE" -eq 1 ]; then
                sed -n '1,80p' "$report"
            fi
            passed=$((passed + 1))
        else
            echo "$test_name: TRACE_FAIL"
            failed=$((failed + 1))
            failed_tests="$failed_tests $test_name"
            if [ "$VERBOSE" -eq 1 ]; then
                sed -n '1,120p' "$report"
            fi
        fi
    else
        echo "$test_name: RUN_FAIL"
        failed=$((failed + 1))
        failed_tests="$failed_tests $test_name"
        if [ "$VERBOSE" -eq 1 ]; then
            sed -n '1,120p' "$trace" || true
        fi
    fi
done

echo "======================================"
echo "Passed: $passed"
echo "Failed: $failed"

if [ "$failed" -gt 0 ]; then
    echo "Failed tests:$failed_tests"
    echo "Trace artifacts kept at: $ARTIFACT_DIR"
    KEEP_ARTIFACTS=1
    exit 1
fi

echo "All trace checks passed!"
if [ "$KEEP_ARTIFACTS" -eq 1 ]; then
    echo "Trace artifacts kept at: $ARTIFACT_DIR"
fi

