#!/bin/bash
#
# SPDX-License-Identifier: MIT OR Apache-2.0
# Copyright (c) 2026 gwz
#

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/../../.." && pwd)"
DEFAULT_DIST="$REPO_ROOT/build/stage2"

cleanup() {
    rm -rf "$DEFAULT_DIST"
}
trap cleanup EXIT

fail() {
    echo "l0c_stage2_default_dist_test: FAIL: $1" >&2
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

cd "$REPO_ROOT"
rm -rf "$DEFAULT_DIST"

./scripts/build-stage2-l0c.sh >/dev/null

assert_file "$DEFAULT_DIST/bin/l0c-stage2"
assert_file "$DEFAULT_DIST/bin/l0c-stage2.native"
assert_no_file "$DEFAULT_DIST/bin/l0c-stage2.c"

env -i PATH="$PATH" "$DEFAULT_DIST/bin/l0c-stage2" --check -P examples hello >/dev/null

echo "l0c_stage2_default_dist_test: PASS"
