#!/bin/bash
#
# SPDX-License-Identifier: MIT OR Apache-2.0
# Copyright (c) 2026 gwz
#

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/../../.." && pwd)"
PREFIX_DIR="$(mktemp -d /tmp/l0_stage2_prefix.XXXXXX)"
PREFIX_DIR="$(cd "$PREFIX_DIR" && pwd -P)"
PROJECT_DIR="$(mktemp -d /tmp/l0_stage2_project.XXXXXX)"
PROJECT_DIR="$(cd "$PROJECT_DIR" && pwd -P)"
INSTALL_LOG="/tmp/l0_stage2_install_prefix_$$.log"
REINSTALL_LOG="/tmp/l0_stage2_install_prefix_reinstall_$$.log"
RUN_OUTPUT="/tmp/l0_stage2_install_prefix_run_$$.out"
ENV_RUN_OUTPUT="/tmp/l0_stage2_install_prefix_env_run_$$.out"

cleanup() {
    rm -rf "$PREFIX_DIR" "$PROJECT_DIR"
    rm -f "$INSTALL_LOG" "$REINSTALL_LOG" "$RUN_OUTPUT" "$ENV_RUN_OUTPUT" "$PROJECT_DIR/hello"
}
trap cleanup EXIT

fail() {
    echo "l0c_stage2_install_prefix_test: FAIL: $1" >&2
    exit 1
}

assert_file() {
    local path="$1"
    [ -f "$path" ] || fail "expected file: $path"
}

assert_symlink_target() {
    local path="$1"
    local expected="$2"
    [ -L "$path" ] || fail "expected symlink: $path"
    local target
    target="$(readlink "$path")"
    [ "$target" = "$expected" ] || fail "expected $path -> $expected, got $target"
}

assert_contains() {
    local path="$1"
    local needle="$2"
    grep -F "$needle" "$path" >/dev/null || fail "expected '$needle' in $path"
}

assert_not_contains() {
    local path="$1"
    local needle="$2"
    if grep -F "$needle" "$path" >/dev/null; then
        fail "did not expect '$needle' in $path"
    fi
}

cd "$REPO_ROOT"
cat > "$PROJECT_DIR/hello.l0" <<'EOF'
module hello;

import std.io;

func main() -> int {
    printl_s("Hello, World!");
    return 0;
}
EOF

if ! make PREFIX="$PREFIX_DIR" install >"$INSTALL_LOG" 2>&1; then
    cat "$INSTALL_LOG" >&2
    fail "make PREFIX=$PREFIX_DIR install failed"
fi

assert_contains "$INSTALL_LOG" "installed self-hosted Stage 2 compiler"
assert_contains "$INSTALL_LOG" "gen-dea-build-tools: L0_CC="
assert_contains "$INSTALL_LOG" "gen-dea-build-tools: L0_CFLAGS="
assert_contains "$INSTALL_LOG" "stage 1/3: building bootstrap Stage 2 compiler"
assert_contains "$INSTALL_LOG" "stage 2/3: self-hosting Stage 2 compiler"
assert_contains "$INSTALL_LOG" "stage 3/3: installing self-hosted Stage 2 compiler"
assert_file "$PREFIX_DIR/bin/l0c-stage2"
assert_file "$PREFIX_DIR/bin/l0c-stage2.native"
assert_file "$PREFIX_DIR/bin/l0-env.sh"
assert_file "$PREFIX_DIR/shared/l0/stdlib/std/fs.l0"
assert_file "$PREFIX_DIR/shared/l0/stdlib/std/io.l0"
assert_file "$PREFIX_DIR/shared/l0/stdlib/std/path.l0"
assert_file "$PREFIX_DIR/shared/runtime/l0_runtime.h"
assert_symlink_target "$PREFIX_DIR/bin/l0c" "l0c-stage2"

if ! env L0_SYSTEM=/tmp/l0_stage2_missing_stdlib_$$ L0_RUNTIME_INCLUDE=/tmp/l0_stage2_missing_runtime_$$ make PREFIX="$PREFIX_DIR" install >"$REINSTALL_LOG" 2>&1; then
    cat "$REINSTALL_LOG" >&2
    fail "make PREFIX=$PREFIX_DIR install failed with leaked L0_* env"
fi

assert_contains "$REINSTALL_LOG" "gen-dea-build-tools: L0_CC="
assert_contains "$REINSTALL_LOG" "gen-dea-build-tools: L0_CFLAGS="

assert_not_contains "$PREFIX_DIR/bin/l0c-stage2" "$REPO_ROOT"
assert_not_contains "$PREFIX_DIR/bin/l0-env.sh" "$REPO_ROOT"

env -i PATH="$PATH" "$PREFIX_DIR/bin/l0c-stage2" --check -P "$PROJECT_DIR" hello >/dev/null
env -i PATH="$PATH" "$PREFIX_DIR/bin/l0c-stage2" --build -P "$PROJECT_DIR" -o "$PROJECT_DIR/hello" hello >/dev/null
"$PROJECT_DIR/hello" >"$RUN_OUTPUT"
assert_contains "$RUN_OUTPUT" "Hello, World!"

env -i PATH="$PATH" bash -lc "source \"$PREFIX_DIR/bin/l0-env.sh\" && [ \"\$L0_HOME\" = \"$PREFIX_DIR\" ] && [ -z \"\${L0_SYSTEM-}\" ] && [ -z \"\${L0_RUNTIME_INCLUDE-}\" ] && l0c --run -P \"$PROJECT_DIR\" hello" >"$ENV_RUN_OUTPUT"
assert_contains "$ENV_RUN_OUTPUT" "Hello, World!"

echo "l0c_stage2_install_prefix_test: PASS"
