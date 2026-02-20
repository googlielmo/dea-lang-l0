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

usage() {
    echo "Usage: $0 [--out <trace-stderr-path>] [--stdout <stdout-path>]"
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
        *)
            echo "Unknown argument: $1"
            usage
            exit 2
            ;;
    esac
done

timestamp="$(date +%Y%m%d_%H%M%S)"
if [ -z "$OUT_PATH" ]; then
    OUT_PATH="/tmp/l0_stage2_parser_trace_${timestamp}.stderr.log"
fi
if [ -z "$STDOUT_PATH" ]; then
    STDOUT_PATH="/tmp/l0_stage2_parser_trace_${timestamp}.stdout.log"
fi

mkdir -p "$(dirname "$OUT_PATH")"
mkdir -p "$(dirname "$STDOUT_PATH")"

cd "$REPO_ROOT"

if ./l0c -P compiler/stage2_l0/src --run --trace-arc --trace-memory compiler/stage2_l0/tests/parser_test.l0 >"$STDOUT_PATH" 2>"$OUT_PATH"; then
    rc=0
else
    rc=$?
fi

echo "trace_stderr=$OUT_PATH"
echo "trace_stdout=$STDOUT_PATH"
echo "exit_code=$rc"

exit "$rc"
