#!/bin/bash
#
# SPDX-License-Identifier: MIT OR Apache-2.0
# Copyright (c) 2026 gwz
#

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/../../.." && pwd)"
BOOTSTRAP_PARENT="$REPO_ROOT/build/tests"
BOOTSTRAP_DIR=""
ALT_DEA_BUILD=""
PROBE_ROOT=""
mkdir -p "$REPO_ROOT/build/tests"
# This path intentionally lives outside the repo tree to test rejection logic.
OUTSIDE_DEA_BUILD="$(mktemp -d /tmp/l0_stage2_outside_dea_build.XXXXXX)"
COND_OUTPUT="$REPO_ROOT/build/tests/l0_stage2_bootstrap_cond_$$.out"
LOGIC_OUTPUT="$REPO_ROOT/build/tests/l0_stage2_bootstrap_logic_$$.out"
GEN_OUTPUT="$REPO_ROOT/build/tests/l0_stage2_bootstrap_gen_$$.c"
HELLO_OUTPUT="$REPO_ROOT/build/tests/l0_stage2_bootstrap_hello_$$"
RUN_OUTPUT="$REPO_ROOT/build/tests/l0_stage2_bootstrap_run_$$.out"
OUTSIDE_LOG="$REPO_ROOT/build/tests/l0_stage2_bootstrap_outside_$$.log"
REPO_ROOT_LOG="$REPO_ROOT/build/tests/l0_stage2_bootstrap_repo_root_$$.log"

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
        env -i PATH="$PATH" SYSTEMROOT="${SYSTEMROOT:-}" COMSPEC="${COMSPEC:-}" WINDIR="${WINDIR:-}" OS="${OS:-}" "$@"
    else
        env -i PATH="$PATH" "$@"
    fi
}

c_output_path() {
    local output_path="$1"
    local dir_path
    local file_name
    dir_path="$(dirname "$output_path")"
    file_name="$(basename "$output_path")"
    case "$file_name" in
        *.*) file_name="${file_name%.*}.c" ;;
        *) file_name="${file_name}.c" ;;
    esac
    printf '%s/%s\n' "$dir_path" "$file_name"
}

# This is the full end-to-end regression for one Stage 2 compiler artifact built
# into an isolated repo-local test Dea build under `build/tests/...`.
#
# It validates:
# - the normal artifact shape (`l0c-stage2`, `l0c-stage2.native`, no retained C
#   by default),
# - direct wrapper usage for `--check`, `--gen`, `--build`, and `--run`,
# - retained-C behavior with `KEEP_C=1`,
# - rejection of invalid `DEA_BUILD_DIR` values (outside-repo and repo-root).
#
# This test intentionally does not exercise the builder's default no-`DEA_BUILD_DIR`
# destination under `build/dea`; that narrower contract is covered separately
# by `l0c_stage2_default_dea_build_test.sh` so `run_tests.py` / `make test-all` do
# not leave `build/dea` behind after a normal test run.

cleanup() {
    if [ -n "$BOOTSTRAP_DIR" ]; then
        rm -rf "$BOOTSTRAP_DIR"
    fi
    if [ -n "$ALT_DEA_BUILD" ]; then
        rm -rf "$ALT_DEA_BUILD"
    fi
    if [ -n "$PROBE_ROOT" ]; then
        rm -rf "$PROBE_ROOT"
    fi
    rm -rf "$OUTSIDE_DEA_BUILD"
    rm -f "$COND_OUTPUT" "$LOGIC_OUTPUT" "$GEN_OUTPUT" "$HELLO_OUTPUT" "$HELLO_OUTPUT.c" "$HELLO_OUTPUT.out" "$RUN_OUTPUT" "$OUTSIDE_LOG" "$REPO_ROOT_LOG"
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

assert_contains() {
    local path="$1"
    local needle="$2"
    grep -F "$needle" "$path" >/dev/null || fail "expected '$needle' in $path"
}

cd "$REPO_ROOT"
mkdir -p "$BOOTSTRAP_PARENT"
BOOTSTRAP_DIR="$(mktemp -d "$BOOTSTRAP_PARENT/l0_stage2_bootstrap.XXXXXX")"
DEA_BUILD_DIR="${BOOTSTRAP_DIR#$REPO_ROOT/}" ./scripts/build-stage2-l0c.sh >/dev/null
STAGE2_L0C="$(stage2_launcher_path "$BOOTSTRAP_DIR/bin/l0c-stage2")"

assert_file "$BOOTSTRAP_DIR/bin/l0c-stage2"
assert_file "$BOOTSTRAP_DIR/bin/l0c-stage2.native"
assert_no_file "$BOOTSTRAP_DIR/bin/l0c-stage2.c"

clean_env_run "$STAGE2_L0C" --check -P examples hello >/dev/null
clean_env_run "$STAGE2_L0C" --check -P examples newdrop >/dev/null
clean_env_run "$STAGE2_L0C" --check -P examples hamurabi >/dev/null
PROBE_ROOT="$(mktemp -d "$BOOTSTRAP_PARENT/l0_stage2_probe.XXXXXX")"
cat > "$PROBE_ROOT/qualified_expr.l0" <<'EOF'
module qualified_expr;

import std.unit;

func main() -> int {
    let maybe = std.unit::present();
    if (maybe != null) {
        return 0;
    }
    return 1;
}
EOF
cat > "$PROBE_ROOT/control_flow_cond.l0" <<'EOF'
module control_flow_cond;

import std.string;

extern func rt_print_int(x: int) -> void;
extern func rt_println() -> void;

func next_value(i: int) -> string {
    if (i == 0) {
        return concat_s("x", "");
    }
    return concat_s("", "");
}

func main() -> int {
    let i: int = 0;
    while (i < 3 && len_s(next_value(i)) > 0) {
        rt_print_int(i);
        rt_println();
        i = i + 1;
    }
    rt_print_int(i);
    rt_println();
    return 0;
}
EOF
cat > "$PROBE_ROOT/logical_expr.l0" <<'EOF'
module logical_expr;

import std.string;

extern func rt_print_int(x: int) -> void;
extern func rt_println() -> void;

func tick(n: int) -> string {
    rt_print_int(n);
    rt_println();
    return concat_s("x", "");
}

func main() -> int {
    let a: bool = false && len_s(tick(7)) > 0;
    let b: bool = true || len_s(tick(8)) > 0;
    let c: bool = false || len_s(tick(9)) > 0;
    let d: bool = true && len_s(tick(10)) > 0;

    if (a) {
        rt_print_int(1);
        rt_println();
    }
    if (b && c && d) {
        rt_print_int(2);
        rt_println();
    }
    return 0;
}
EOF
clean_env_run "$STAGE2_L0C" --check -P "$(native_path "$PROBE_ROOT")" qualified_expr >/dev/null
clean_env_run "$STAGE2_L0C" --run -P "$(native_path "$PROBE_ROOT")" control_flow_cond > "$COND_OUTPUT"
assert_contains "$COND_OUTPUT" "0"
assert_contains "$COND_OUTPUT" "1"
if grep -x "2" "$COND_OUTPUT" >/dev/null; then
    fail "expected control_flow_cond loop to stop after i=1"
fi
clean_env_run "$STAGE2_L0C" --run -P "$(native_path "$PROBE_ROOT")" logical_expr > "$LOGIC_OUTPUT"
assert_contains "$LOGIC_OUTPUT" "9"
assert_contains "$LOGIC_OUTPUT" "10"
assert_contains "$LOGIC_OUTPUT" "2"
if grep -x "7" "$LOGIC_OUTPUT" >/dev/null; then
    fail "expected logical_expr to short-circuit false && RHS"
fi
if grep -x "8" "$LOGIC_OUTPUT" >/dev/null; then
    fail "expected logical_expr to short-circuit true || RHS"
fi
clean_env_run "$STAGE2_L0C" --gen --no-line-directives -P examples hello > "$GEN_OUTPUT"
rm -f "$GEN_OUTPUT"
if is_windows_host; then
    HELLO_OUTPUT="$HELLO_OUTPUT.exe"
fi
clean_env_run "$STAGE2_L0C" --build --keep-c -P examples -o "$(native_path "$HELLO_OUTPUT")" hello >/dev/null
assert_file "$HELLO_OUTPUT"
assert_file "$(c_output_path "$HELLO_OUTPUT")"
"$HELLO_OUTPUT" > "$HELLO_OUTPUT.out"
assert_contains "$HELLO_OUTPUT.out" "Hello, World!"
clean_env_run "$STAGE2_L0C" --run -P examples hello > "$RUN_OUTPUT"
assert_contains "$RUN_OUTPUT" "Hello, World!"

ALT_DEA_BUILD="$(mktemp -d "$BOOTSTRAP_PARENT/l0_stage2_bootstrap_keepc.XXXXXX")"
DEA_BUILD_DIR="${ALT_DEA_BUILD#$REPO_ROOT/}" KEEP_C=1 ./scripts/build-stage2-l0c.sh >/dev/null

assert_file "$ALT_DEA_BUILD/bin/l0c-stage2"
assert_file "$ALT_DEA_BUILD/bin/l0c-stage2.native"
assert_file "$ALT_DEA_BUILD/bin/l0c-stage2.c"

if DEA_BUILD_DIR="$OUTSIDE_DEA_BUILD" ./scripts/build-stage2-l0c.sh >"$OUTSIDE_LOG" 2>&1; then
    rm -f "$OUTSIDE_LOG"
    fail "expected outside-repo DEA_BUILD_DIR rejection"
fi
rm -f "$OUTSIDE_LOG"

if DEA_BUILD_DIR="." ./scripts/build-stage2-l0c.sh >"$REPO_ROOT_LOG" 2>&1; then
    rm -f "$REPO_ROOT_LOG"
    fail "expected repo-root DEA_BUILD_DIR rejection"
fi
rm -f "$REPO_ROOT_LOG"

echo "l0c_stage2_bootstrap_test: PASS"
