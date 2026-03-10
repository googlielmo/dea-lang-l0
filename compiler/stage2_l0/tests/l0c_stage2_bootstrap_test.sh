#!/bin/bash
#
# SPDX-License-Identifier: MIT OR Apache-2.0
# Copyright (c) 2026 gwz
#

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/../../.." && pwd)"
DEFAULT_DIST="$REPO_ROOT/build/stage2"
ALT_DIST="$REPO_ROOT/build/stage2-alt"
OUTSIDE_DIST="$(mktemp -d /tmp/l0_stage2_outside_dist.XXXXXX)"

cleanup() {
    rm -rf "$ALT_DIST" "$OUTSIDE_DIST"
}
trap cleanup EXIT

fail() {
    echo "l0c_stage2_bootstrap_test: FAIL: $1" >&2
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

./scripts/build-stage2-l0c.sh

assert_file "$DEFAULT_DIST/bin/l0c-stage2"
assert_file "$DEFAULT_DIST/bin/l0c-stage2.native"
assert_no_file "$DEFAULT_DIST/bin/l0c-stage2.c"

env -i PATH="$PATH" "$DEFAULT_DIST/bin/l0c-stage2" --check -P examples hello >/dev/null
env -i PATH="$PATH" "$DEFAULT_DIST/bin/l0c-stage2" --gen --no-line-directives -P examples hello > /tmp/l0_stage2_bootstrap_gen_$$.c
rm -f /tmp/l0_stage2_bootstrap_gen_$$.c

DIST_DIR=build/stage2-alt KEEP_C=1 ./scripts/build-stage2-l0c.sh

assert_file "$ALT_DIST/bin/l0c-stage2"
assert_file "$ALT_DIST/bin/l0c-stage2.native"
assert_file "$ALT_DIST/bin/l0c-stage2.c"

if DIST_DIR="$OUTSIDE_DIST" ./scripts/build-stage2-l0c.sh >/tmp/l0_stage2_bootstrap_outside_$$.log 2>&1; then
    rm -f /tmp/l0_stage2_bootstrap_outside_$$.log
    fail "expected outside-repo DIST_DIR rejection"
fi
rm -f /tmp/l0_stage2_bootstrap_outside_$$.log

echo "l0c_stage2_bootstrap_test: PASS"
