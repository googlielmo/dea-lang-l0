#!/bin/bash
#
# SPDX-License-Identifier: MIT OR Apache-2.0
# Copyright (c) 2026 gwz
#

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/../../.." && pwd)"

# Use an isolated temp directory instead of moving/clobbering the real
# build/dea, which races with other parallel tests that depend on it.
mkdir -p "$REPO_ROOT/build/tests"
TEST_DEA_BUILD="$(mktemp -d "$REPO_ROOT/build/tests/l0_stage2_default_dea_build.XXXXXX")"

cleanup() {
    rm -rf "$TEST_DEA_BUILD"
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

is_windows_host() {
    case "$(uname -s)" in
        CYGWIN*|MINGW*|MSYS*) return 0 ;;
    esac
    return 1
}

clean_env_run() {
    if is_windows_host; then
        env -i PATH="$PATH" SYSTEMROOT="${SYSTEMROOT:-}" COMSPEC="${COMSPEC:-}" WINDIR="${WINDIR:-}" OS="${OS:-}" TEMP="${TEMP:-}" TMP="${TMP:-}" "$@"
    else
        env -i PATH="$PATH" "$@"
    fi
}

cd "$REPO_ROOT"

DEA_BUILD_DIR="$TEST_DEA_BUILD" ./scripts/build-stage2-l0c.sh >/dev/null

assert_file "$TEST_DEA_BUILD/bin/l0c-stage2"
assert_file "$TEST_DEA_BUILD/bin/l0c-stage2.native"
assert_no_file "$TEST_DEA_BUILD/bin/l0c-stage2.c"

clean_env_run "$TEST_DEA_BUILD/bin/l0c-stage2" --check -P examples hello >/dev/null

echo "l0c_stage2_default_dea_build_test: PASS"
