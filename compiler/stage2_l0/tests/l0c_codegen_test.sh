#!/bin/bash
#
# SPDX-License-Identifier: MIT OR Apache-2.0
# Copyright (c) 2026 gwz
#

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/../../.." && pwd)"
FIXTURE_ROOT="$SCRIPT_DIR/fixtures/backend_golden"
REFRESH_SCRIPT="$REPO_ROOT/scripts/refresh_stage2_backend_goldens.py"
ARTIFACT_DIR="$(mktemp -d /tmp/l0_stage2_codegen_tests.XXXXXX)"
BOOTSTRAP_PARENT="$REPO_ROOT/build/tests"
BOOTSTRAP_DIR=""
KEEP_ARTIFACTS="${KEEP_ARTIFACTS:-0}"

cleanup() {
    if [ "$KEEP_ARTIFACTS" -eq 0 ]; then
        rm -rf "$ARTIFACT_DIR"
        if [ -n "$BOOTSTRAP_DIR" ]; then
            rm -rf "$BOOTSTRAP_DIR"
        fi
    fi
}
trap cleanup EXIT

fail() {
    local message="$1"
    echo "l0c_codegen_test: FAIL: $message" >&2
    echo "l0c_codegen_test: artifacts=$ARTIFACT_DIR" >&2
    if [ -n "$BOOTSTRAP_DIR" ]; then
        echo "l0c_codegen_test: bootstrap=$BOOTSTRAP_DIR" >&2
    fi
    KEEP_ARTIFACTS=1
    exit 1
}

detect_cc() {
    if [ -n "${CC:-}" ] && command -v "$CC" >/dev/null 2>&1; then
        printf '%s\n' "$CC"
        return 0
    fi
    for candidate in tcc gcc clang cc; do
        if command -v "$candidate" >/dev/null 2>&1; then
            printf '%s\n' "$candidate"
            return 0
        fi
    done
    return 1
}

compile_generated_c() {
    local compiler="$1"
    local src="$2"
    local exe="$3"
    case "$(basename "$compiler")" in
        tcc*)
            "$compiler" "$src" -o "$exe" -I "$REPO_ROOT/compiler/shared/runtime" -std=c99 -Wall -pedantic
            ;;
        gcc*|clang*|cc)
            "$compiler" "$src" -o "$exe" -I "$REPO_ROOT/compiler/shared/runtime" -std=c99 -Wall -Wextra -Wno-unused -Wno-parentheses -pedantic-errors
            ;;
        *)
            "$compiler" "$src" -o "$exe" -I "$REPO_ROOT/compiler/shared/runtime"
            ;;
    esac
}

normalize_text_file() {
    local src="$1"
    local dst="$2"
    python3 - "$src" "$dst" <<'PY'
from pathlib import Path
import sys

src = Path(sys.argv[1])
dst = Path(sys.argv[2])
text = src.read_text(encoding="utf-8")
text = text.replace("\r\n", "\n").replace("\r", "\n")
dst.write_text(text.rstrip("\n") + "\n", encoding="utf-8")
PY
}

cd "$REPO_ROOT"
python3 "$REFRESH_SCRIPT" --check "$@"

mkdir -p "$BOOTSTRAP_PARENT"
BOOTSTRAP_DIR="$(mktemp -d "$BOOTSTRAP_PARENT/l0_stage2_codegen.XXXXXX")"
DEA_BUILD_DIR="${BOOTSTRAP_DIR#$REPO_ROOT/}" ./scripts/build-stage2-l0c.sh >/dev/null
STAGE2_L0C="$BOOTSTRAP_DIR/bin/l0c-stage2"

compiler=""
if find "$FIXTURE_ROOT" -name '*.expected.out' -print -quit | grep -q .; then
    compiler="$(detect_cc || true)"
    if [ -z "$compiler" ]; then
        fail "no C compiler found for runtime parity checks"
    fi
fi

status=0
for entry_file in "$FIXTURE_ROOT"/*/entry_module.txt; do
    [ -f "$entry_file" ] || continue
    case_name="$(basename "$(dirname "$entry_file")")"
    if [ "$#" -gt 0 ]; then
        skip=1
        for wanted in "$@"; do
            if [ "$wanted" = "$case_name" ]; then
                skip=0
                break
            fi
        done
        [ "$skip" -eq 1 ] && continue
    fi

    case_dir="$(dirname "$entry_file")"
    entry_module="$(tr -d '\r\n' < "$entry_file")"
    generated="$ARTIFACT_DIR/${case_name}.generated.c"
    normalized_generated="$ARTIFACT_DIR/${case_name}.generated.normalized.c"
    normalized_expected="$ARTIFACT_DIR/${case_name}.expected.normalized.c"
    expected="$case_dir/${case_name}.golden.c"

    if ! "$STAGE2_L0C" --gen --no-line-directives -P "$case_dir" "$entry_module" > "$generated"; then
        echo "$case_name: GEN_FAIL" >&2
        status=1
        continue
    fi

    normalize_text_file "$expected" "$normalized_expected"
    normalize_text_file "$generated" "$normalized_generated"

    if ! diff -u "$normalized_expected" "$normalized_generated" > "$ARTIFACT_DIR/${case_name}.diff"; then
        echo "$case_name: DIFF_FAIL" >&2
        cat "$ARTIFACT_DIR/${case_name}.diff" >&2
        status=1
        continue
    fi

    expected_out="$case_dir/${case_name}.expected.out"
    if [ -f "$expected_out" ]; then
        exe="$ARTIFACT_DIR/${case_name}.out"
        actual_out="$ARTIFACT_DIR/${case_name}.stdout"
        compile_generated_c "$compiler" "$generated" "$exe"
        "$exe" > "$actual_out"
        if ! diff -u "$expected_out" "$actual_out" > "$ARTIFACT_DIR/${case_name}.stdout.diff"; then
            echo "$case_name: RUNTIME_DIFF_FAIL" >&2
            cat "$ARTIFACT_DIR/${case_name}.stdout.diff" >&2
            status=1
            continue
        fi
    fi

    echo "$case_name: OK"
done

if [ "$status" -ne 0 ]; then
    echo "l0c_codegen_test: artifacts=$ARTIFACT_DIR" >&2
    echo "l0c_codegen_test: bootstrap=$BOOTSTRAP_DIR" >&2
    KEEP_ARTIFACTS=1
fi

exit "$status"
