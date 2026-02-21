#!/bin/bash
#
# SPDX-License-Identifier: MIT OR Apache-2.0
# Copyright (c) 2026 gwz
#

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"

OUT_PATH=""
STDOUT_PATH=""
TEST=""

usage() {
    echo "Usage: $0 [--out <trace-stderr-path>] [--stdout <stdout-path>] <test-name>"
    echo "  --out <trace-stderr-path>   Path to write the trace stderr output (default: /tmp/l0_stage2_test_trace_<timestamp>.stderr.log)"
    echo "  --stdout <stdout-path>      Path to write the trace stdout output (default: /tmp/l0_stage2_test_trace_<timestamp>.stdout.log)"
    echo "  <test-name>                 Test name in compiler/stage2_l0/tests (with or without .l0, required)"
    echo
    echo "Available tests in compiler/stage2_l0/tests:"
    if compgen -G "$SCRIPT_DIR/tests/*.l0" > /dev/null; then
        for test_file in "$SCRIPT_DIR"/tests/*.l0; do
            basename "$test_file" .l0
        done | sort | sed 's/^/  - /'
    else
        echo "  (none found)"
    fi
}

while [ $# -gt 0 ]; do
    case "$1" in
        --out)
            if [ $# -lt 2 ]; then
                usage
                exit 2
            fi
            OUT_PATH="$2"
            shift 2
            ;;
        --stdout)
            if [ $# -lt 2 ]; then
                usage
                exit 2
            fi
            STDOUT_PATH="$2"
            shift 2
            ;;
        -h|--help)
            usage
            exit 0
            ;;
        # read the first non-option argument as the test name
        *)
          if [ -z "$TEST" ]; then
              TEST="$1"
              shift
              continue
            else
              echo "Unknown argument: $1"
              usage
              exit 2
          fi
          ;;
    esac
done

if [ -z "$TEST" ]; then
    echo "Error: No test name specified."
    usage
    exit 2
fi

if [[ "$TEST" == *.l0 ]]; then
    TEST_FILE="$TEST"
else
    TEST_FILE="${TEST}.l0"
fi

if [ ! -f "$SCRIPT_DIR/tests/$TEST_FILE" ]; then
    echo "Error: Test file not found: compiler/stage2_l0/tests/$TEST_FILE"
    usage
    exit 2
fi

timestamp="$(date +%Y%m%d_%H%M%S)"
if [ -z "$OUT_PATH" ]; then
    OUT_PATH="/tmp/l0_stage2_test_trace_${timestamp}.stderr.log"
fi
if [ -z "$STDOUT_PATH" ]; then
    STDOUT_PATH="/tmp/l0_stage2_test_trace_${timestamp}.stdout.log"
fi

mkdir -p "$(dirname "$OUT_PATH")"
mkdir -p "$(dirname "$STDOUT_PATH")"

cd "$REPO_ROOT"

if ./l0c -P compiler/stage2_l0/src --run --trace-arc --trace-memory "compiler/stage2_l0/tests/$TEST_FILE" >"$STDOUT_PATH" 2>"$OUT_PATH"; then
    rc=0
else
    rc=$?
fi

echo "trace_stderr=$OUT_PATH"
echo "trace_stdout=$STDOUT_PATH"
echo "exit_code=$rc"
echo
echo "triage with:"
echo
echo "\"$SCRIPT_DIR/check_trace_log.py\" \"$OUT_PATH\" --triage"
exit "$rc"
