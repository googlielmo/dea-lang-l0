#!/bin/bash
#
# SPDX-License-Identifier: MIT OR Apache-2.0
# Copyright (c) 2026 gwz
#

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/../../.." && pwd)"
mkdir -p "$REPO_ROOT/build/tests"
PREFIX_DIR="$(mktemp -d "$REPO_ROOT/build/tests/l0_stage2_prefix.XXXXXX")"
PREFIX_DIR="$(cd "$PREFIX_DIR" && pwd -P)"
PROJECT_DIR="$(mktemp -d "$REPO_ROOT/build/tests/l0_stage2_project.XXXXXX")"
PROJECT_DIR="$(cd "$PROJECT_DIR" && pwd -P)"
INSTALL_LOG="$REPO_ROOT/build/tests/l0_stage2_install_prefix_$$.log"
REINSTALL_LOG="$REPO_ROOT/build/tests/l0_stage2_install_prefix_reinstall_$$.log"
RUN_OUTPUT="$REPO_ROOT/build/tests/l0_stage2_install_prefix_run_$$.out"
ENV_RUN_OUTPUT="$REPO_ROOT/build/tests/l0_stage2_install_prefix_env_run_$$.out"
VERSION_OUTPUT="$REPO_ROOT/build/tests/l0_stage2_install_prefix_version_$$.out"
NATIVE_VERSION_OUTPUT="$REPO_ROOT/build/tests/l0_stage2_install_prefix_native_version_$$.out"
NORMALIZED_VERSION_OUTPUT="$REPO_ROOT/build/tests/l0_stage2_install_prefix_version_normalized_$$.out"
NORMALIZED_NATIVE_VERSION_OUTPUT="$REPO_ROOT/build/tests/l0_stage2_install_prefix_native_version_normalized_$$.out"

is_windows_host() {
    case "$(uname -s)" in
        CYGWIN*|MINGW*|MSYS*) return 0 ;;
    esac
    return 1
}

native_path() {
    local path="$1"
    if is_windows_host; then
        cygpath -w "$path"
    else
        printf '%s\n' "$path"
    fi
}

stage2_launcher_path() {
    local base="$1"
    if is_windows_host && [ -f "$base.cmd" ]; then
        native_path "$base.cmd"
    else
        printf '%s\n' "$base"
    fi
}

clean_env_run() {
    if is_windows_host; then
        env -i PATH="$PATH" SYSTEMROOT="${SYSTEMROOT:-}" COMSPEC="${COMSPEC:-}" WINDIR="${WINDIR:-}" "$@"
    else
        env -i PATH="$PATH" "$@"
    fi
}

normalize_newlines() {
    local src="$1"
    local dst="$2"
    tr -d '\r' < "$src" > "$dst"
}

cleanup() {
    rm -rf "$PREFIX_DIR" "$PROJECT_DIR"
    rm -f "$INSTALL_LOG" "$REINSTALL_LOG" "$RUN_OUTPUT" "$ENV_RUN_OUTPUT" "$VERSION_OUTPUT" "$NATIVE_VERSION_OUTPUT" \
        "$NORMALIZED_VERSION_OUTPUT" "$NORMALIZED_NATIVE_VERSION_OUTPUT" "$PROJECT_DIR/hello"
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

assert_version_report() {
    local path="$1"
    assert_contains "$path" "Dea language / L0 compiler (Stage 2)"
    assert_contains "$path" "build: "
    assert_contains "$path" "build time: "
    assert_contains "$path" "commit: "
    assert_contains "$path" "host: "
    assert_contains "$path" "compiler: "
    assert_not_contains "$path" "tree: "
    assert_not_contains "$path" "build id: "
    assert_not_contains "$path" "built at: "
    assert_not_contains "$path" "compiler version: "
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

if ! make PREFIX="$(native_path "$PREFIX_DIR")" install >"$INSTALL_LOG" 2>&1; then
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
if is_windows_host; then
    assert_file "$PREFIX_DIR/bin/l0-env.cmd"
fi
assert_file "$PREFIX_DIR/shared/l0/stdlib/std/fs.l0"
assert_file "$PREFIX_DIR/shared/l0/stdlib/std/io.l0"
assert_file "$PREFIX_DIR/shared/l0/stdlib/std/path.l0"
assert_file "$PREFIX_DIR/shared/runtime/l0_runtime.h"
if is_windows_host; then
    assert_file "$PREFIX_DIR/bin/l0c"
else
    assert_symlink_target "$PREFIX_DIR/bin/l0c" "l0c-stage2"
fi

if ! env L0_SYSTEM="$(native_path "/tmp/l0_stage2_missing_stdlib_$$")" L0_RUNTIME_INCLUDE="$(native_path "/tmp/l0_stage2_missing_runtime_$$")" make PREFIX="$(native_path "$PREFIX_DIR")" install >"$REINSTALL_LOG" 2>&1; then
    cat "$REINSTALL_LOG" >&2
    fail "make PREFIX=$PREFIX_DIR install failed with leaked L0_* env"
fi

assert_contains "$REINSTALL_LOG" "gen-dea-build-tools: L0_CC="
assert_contains "$REINSTALL_LOG" "gen-dea-build-tools: L0_CFLAGS="

assert_not_contains "$PREFIX_DIR/bin/l0c-stage2" "$REPO_ROOT"
assert_not_contains "$PREFIX_DIR/bin/l0-env.sh" "$REPO_ROOT"

clean_env_run "$(stage2_launcher_path "$PREFIX_DIR/bin/l0c-stage2")" --version >"$VERSION_OUTPUT"
clean_env_run "$(native_path "$PREFIX_DIR/bin/l0c-stage2.native")" --version >"$NATIVE_VERSION_OUTPUT"
assert_version_report "$VERSION_OUTPUT"
assert_version_report "$NATIVE_VERSION_OUTPUT"
normalize_newlines "$VERSION_OUTPUT" "$NORMALIZED_VERSION_OUTPUT"
normalize_newlines "$NATIVE_VERSION_OUTPUT" "$NORMALIZED_NATIVE_VERSION_OUTPUT"
cmp -s "$NORMALIZED_VERSION_OUTPUT" "$NORMALIZED_NATIVE_VERSION_OUTPUT" || fail "wrapper and native --version output must match"

clean_env_run "$(stage2_launcher_path "$PREFIX_DIR/bin/l0c-stage2")" --check -P "$(native_path "$PROJECT_DIR")" hello >/dev/null
HELLO_BIN="$PROJECT_DIR/hello"
if is_windows_host; then
    HELLO_BIN="$HELLO_BIN.exe"
fi
clean_env_run "$(stage2_launcher_path "$PREFIX_DIR/bin/l0c-stage2")" --build -P "$(native_path "$PROJECT_DIR")" -o "$(native_path "$HELLO_BIN")" hello >/dev/null
"$HELLO_BIN" >"$RUN_OUTPUT"
assert_contains "$RUN_OUTPUT" "Hello, World!"

env -i PATH="$PATH" bash -lc "source \"$PREFIX_DIR/bin/l0-env.sh\" && [ \"\$L0_HOME\" = \"$PREFIX_DIR\" ] && [ -z \"\${L0_SYSTEM-}\" ] && [ -z \"\${L0_RUNTIME_INCLUDE-}\" ] && l0c --run -P \"$(native_path "$PROJECT_DIR")\" hello" >"$ENV_RUN_OUTPUT"
assert_contains "$ENV_RUN_OUTPUT" "Hello, World!"

echo "l0c_stage2_install_prefix_test: PASS"
