#!/bin/bash
#
# SPDX-License-Identifier: MIT OR Apache-2.0
# Copyright (c) 2026 gwz
#

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/../../.." && pwd)"
DEFAULT_DEA_BUILD="$REPO_ROOT/build/dea"
BACKUP_ROOT=""
BACKUP_DEA_BUILD=""

cleanup() {
    rm -rf "$DEFAULT_DEA_BUILD"
    if [ -n "$BACKUP_DEA_BUILD" ] && [ -e "$BACKUP_DEA_BUILD" ]; then
        mv "$BACKUP_DEA_BUILD" "$DEFAULT_DEA_BUILD"
    fi
    if [ -n "$BACKUP_ROOT" ]; then
        rm -rf "$BACKUP_ROOT"
    fi
}
trap cleanup EXIT

fail() {
    echo "l0c_stage2_default_dea_build_test: FAIL: $1" >&2
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
if [ -e "$DEFAULT_DEA_BUILD" ]; then
    mkdir -p "$REPO_ROOT/build/tests"
    BACKUP_ROOT="$(mktemp -d "$REPO_ROOT/build/tests/l0_stage2_default_dea_backup.XXXXXX")"
    BACKUP_DEA_BUILD="$BACKUP_ROOT/dea"
    mv "$DEFAULT_DEA_BUILD" "$BACKUP_DEA_BUILD"
fi
rm -rf "$DEFAULT_DEA_BUILD"

./scripts/build-stage2-l0c.sh >/dev/null

assert_file "$DEFAULT_DEA_BUILD/bin/l0c-stage2"
assert_file "$DEFAULT_DEA_BUILD/bin/l0c-stage2.native"
assert_no_file "$DEFAULT_DEA_BUILD/bin/l0c-stage2.c"

env -i PATH="$PATH" "$DEFAULT_DEA_BUILD/bin/l0c-stage2" --check -P examples hello >/dev/null

echo "l0c_stage2_default_dea_build_test: PASS"
