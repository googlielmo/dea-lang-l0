#!/bin/bash
#
# SPDX-License-Identifier: MIT OR Apache-2.0
# Copyright (c) 2026 gwz
#

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/../../.." && pwd)"
mkdir -p "$REPO_ROOT/build"
TMP_DIR="$(mktemp -d "$REPO_ROOT/build/l0c-stage2-help-test.XXXXXX")"
DEA_BUILD_DIR="$TMP_DIR/dea"

cleanup() {
    rm -rf "$TMP_DIR"
}
trap cleanup EXIT

fail() {
    echo "l0c_stage2_help_output_test: FAIL: $1" >&2
    exit 1
}

assert_contains() {
    local path="$1"
    local text="$2"
    grep -F "$text" "$path" >/dev/null || fail "expected '$text' in $path"
}

assert_empty() {
    local path="$1"
    [ ! -s "$path" ] || fail "expected empty file: $path"
}

cd "$REPO_ROOT"
DEA_BUILD_DIR="$DEA_BUILD_DIR" ./scripts/build-stage2-l0c.sh >/dev/null

HELP_STDOUT="$TMP_DIR/help.stdout"
HELP_STDERR="$TMP_DIR/help.stderr"
if ! env -i PATH="$PATH" "$DEA_BUILD_DIR/bin/l0c-stage2" --help >"$HELP_STDOUT" 2>"$HELP_STDERR"; then
    fail "--help should exit successfully"
fi

assert_contains "$HELP_STDOUT" "usage: l0c [-h]"
assert_contains "$HELP_STDOUT" "Dea language / L0 compiler (Stage 2)"
assert_contains "$HELP_STDOUT" "  -h, --help            show this help message and exit"
assert_contains "$HELP_STDOUT" "  --version             show compiler version and exit"
assert_empty "$HELP_STDERR"

VERSION_STDOUT="$TMP_DIR/version.stdout"
VERSION_STDERR="$TMP_DIR/version.stderr"
if ! env -i PATH="$PATH" "$DEA_BUILD_DIR/bin/l0c-stage2" --version >"$VERSION_STDOUT" 2>"$VERSION_STDERR"; then
    fail "--version should exit successfully"
fi

assert_contains "$VERSION_STDOUT" "Dea language / L0 compiler (Stage 2)"
assert_empty "$VERSION_STDERR"

VERBOSE_STDOUT="$TMP_DIR/verbose.stdout"
VERBOSE_STDERR="$TMP_DIR/verbose.stderr"
if ! env -i PATH="$PATH" "$DEA_BUILD_DIR/bin/l0c-stage2" -v --check -P examples hello >"$VERBOSE_STDOUT" 2>"$VERBOSE_STDERR"; then
    fail "-v --check should exit successfully"
fi

assert_contains "$VERBOSE_STDERR" "Dea language / L0 compiler (Stage 2)"

VERBOSE_FAIL_STDOUT="$TMP_DIR/verbose-fail.stdout"
VERBOSE_FAIL_STDERR="$TMP_DIR/verbose-fail.stderr"
set +e
env -i PATH="$PATH" "$DEA_BUILD_DIR/bin/l0c-stage2" -v >"$VERBOSE_FAIL_STDOUT" 2>"$VERBOSE_FAIL_STDERR"
RC=$?
set -e
if [ "$RC" -ne 2 ]; then
    fail "expected -v without target exit code 2, got $RC"
fi

assert_empty "$VERBOSE_FAIL_STDOUT"
assert_contains "$VERBOSE_FAIL_STDERR" "Dea language / L0 compiler (Stage 2)"
assert_contains "$VERBOSE_FAIL_STDERR" "usage: l0c [-h] [--version]"
assert_contains "$VERBOSE_FAIL_STDERR" "error: [L0C-2021] missing required target module/file name"

NOARGS_STDOUT="$TMP_DIR/noargs.stdout"
NOARGS_STDERR="$TMP_DIR/noargs.stderr"
set +e
env -i PATH="$PATH" "$DEA_BUILD_DIR/bin/l0c-stage2" >"$NOARGS_STDOUT" 2>"$NOARGS_STDERR"
RC=$?
set -e
if [ "$RC" -ne 2 ]; then
    fail "expected no-args exit code 2, got $RC"
fi

assert_empty "$NOARGS_STDOUT"
assert_contains "$NOARGS_STDERR" "usage: l0c [-h] [--version]"
assert_contains "$NOARGS_STDERR" "error: [L0C-2021] missing required target module/file name"

echo "l0c_stage2_help_output_test: PASS"
