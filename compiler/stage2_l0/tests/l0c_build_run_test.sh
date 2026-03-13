#!/bin/bash
#
# SPDX-License-Identifier: MIT OR Apache-2.0
# Copyright (c) 2026 gwz
#

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/../../.." && pwd)"
FIXTURE_ROOT="$SCRIPT_DIR/fixtures/driver"
mkdir -p "$REPO_ROOT/build/tests"
WORK_DIR="$(mktemp -d "$REPO_ROOT/build/tests/l0_stage2_build_run_test.XXXXXX")"
BOOTSTRAP_PARENT="$REPO_ROOT/build/tests"
BOOTSTRAP_DIR=""

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

cleanup() {
    rm -rf "$WORK_DIR"
    if [ -n "$BOOTSTRAP_DIR" ]; then
        rm -rf "$BOOTSTRAP_DIR"
    fi
}
trap cleanup EXIT

fail() {
    echo "l0c_build_run_test: FAIL: $1" >&2
    echo "l0c_build_run_test: work=$WORK_DIR" >&2
    if [ -n "$BOOTSTRAP_DIR" ]; then
        echo "l0c_build_run_test: bootstrap=$BOOTSTRAP_DIR" >&2
    fi
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

assert_text_equals() {
    local path="$1"
    local expected="$2"
    local actual
    actual="$(cat "$path")"
    [ "$actual" = "$expected" ] || fail "unexpected content in $path"
}

cd "$REPO_ROOT"
mkdir -p "$BOOTSTRAP_PARENT"
BOOTSTRAP_DIR="$(mktemp -d "$BOOTSTRAP_PARENT/l0_stage2_buildrun.XXXXXX")"
DEA_BUILD_DIR="${BOOTSTRAP_DIR#$REPO_ROOT/}" ./scripts/build-stage2-l0c.sh >/dev/null
STAGE2_L0C="$(stage2_launcher_path "$BOOTSTRAP_DIR/bin/l0c-stage2")"
STAGE2_NATIVE="$(native_path "$BOOTSTRAP_DIR/bin/l0c-stage2.native")"
OK_MAIN_BIN="$WORK_DIR/ok_main.bin"
BYTE_MAIN_BIN="$WORK_DIR/byte_main.bin"
if is_windows_host; then
    OK_MAIN_BIN="$OK_MAIN_BIN.exe"
    BYTE_MAIN_BIN="$BYTE_MAIN_BIN.exe"
fi

"$STAGE2_L0C" --build --keep-c -P "$(native_path "$FIXTURE_ROOT")" -o "$(native_path "$OK_MAIN_BIN")" ok_main >"$WORK_DIR/build_ok.log" 2>&1
assert_file "$OK_MAIN_BIN"
assert_file "${OK_MAIN_BIN%.*}.c"
"$OK_MAIN_BIN" >"$WORK_DIR/ok_main.stdout" 2>"$WORK_DIR/ok_main.stderr"
assert_text_equals "$WORK_DIR/ok_main.stdout" ""

"$STAGE2_NATIVE" --run -P "$(native_path "$FIXTURE_ROOT")" argv_dump -- "two words" "rock'n'roll" >"$WORK_DIR/argv.out" 2>&1
cat >"$WORK_DIR/argv.expected" <<'EOF'
3
two words
rock'n'roll
EOF
tail -n 3 "$WORK_DIR/argv.out" >"$WORK_DIR/argv.tail"
if ! diff -u "$WORK_DIR/argv.expected" "$WORK_DIR/argv.tail" >"$WORK_DIR/argv.diff"; then
    echo "l0c_build_run_test: argv diff:" >&2
    cat "$WORK_DIR/argv.diff" >&2
    echo "l0c_build_run_test: argv raw output (sed -n l):" >&2
    sed -n 'l' "$WORK_DIR/argv.out" >&2
    echo "l0c_build_run_test: argv tail raw output (sed -n l):" >&2
    sed -n 'l' "$WORK_DIR/argv.tail" >&2
    echo "l0c_build_run_test: argv tail bytes (od -An -tx1 -c):" >&2
    od -An -tx1 -c "$WORK_DIR/argv.tail" >&2
    fail "argv forwarding output mismatch"
fi

"$STAGE2_L0C" --run -P examples demo -- add 2 3 >"$WORK_DIR/demo.out" 2>&1
tail -n 1 "$WORK_DIR/demo.out" >"$WORK_DIR/demo.tail"
assert_text_equals "$WORK_DIR/demo.tail" "= 5"

set +e
"$STAGE2_L0C" --run -P "$(native_path "$FIXTURE_ROOT")" exit_seven >"$WORK_DIR/exit_seven.out" 2>&1
rc=$?
set -e
if [ "$rc" -eq 0 ]; then
    fail "expected exit_seven to return a non-zero exit code"
fi
[ "$rc" -eq 7 ] || fail "expected --run exit code 7"

"$STAGE2_L0C" --run --keep-c -P "$(native_path "$FIXTURE_ROOT")" -o "$(native_path "$WORK_DIR/kept-name")" ok_main >"$WORK_DIR/run_keep.log" 2>&1
assert_file "$WORK_DIR/kept-name.c"

"$STAGE2_L0C" --run -P "$(native_path "$FIXTURE_ROOT")" -o "$(native_path "$WORK_DIR/ignored-output")" ok_main >"$WORK_DIR/run_warn.log" 2>&1
assert_contains "$WORK_DIR/run_warn.log" "L0C-0017"
assert_no_file "$WORK_DIR/ignored-output"

mkdir "$WORK_DIR/empty-bin"
if env -u L0_CC -u CC PATH="$WORK_DIR/empty-bin" "$STAGE2_NATIVE" --build -P "$(native_path "$FIXTURE_ROOT")" ok_main >"$WORK_DIR/no_cc.log" 2>&1; then
    fail "expected no-compiler build to fail"
fi
assert_contains "$WORK_DIR/no_cc.log" "L0C-0009"

if "$STAGE2_L0C" --build --c-compiler false -P "$(native_path "$FIXTURE_ROOT")" ok_main >"$WORK_DIR/compile_fail.log" 2>&1; then
    fail "expected explicit failing compiler to fail"
fi
assert_contains "$WORK_DIR/compile_fail.log" "L0C-0010"

if "$STAGE2_L0C" --build --runtime-lib "$(native_path "$WORK_DIR/missing-lib")" -P "$(native_path "$FIXTURE_ROOT")" ok_main >"$WORK_DIR/runtime_lib_missing.log" 2>&1; then
    fail "expected missing runtime-lib directory to fail"
fi
assert_contains "$WORK_DIR/runtime_lib_missing.log" "L0C-0014"

mkdir "$WORK_DIR/empty-lib"
if "$STAGE2_L0C" --build --runtime-lib "$(native_path "$WORK_DIR/empty-lib")" -P "$(native_path "$FIXTURE_ROOT")" ok_main >"$WORK_DIR/runtime_lib_empty.log" 2>&1; then
    fail "expected empty runtime-lib directory to fail"
fi
assert_contains "$WORK_DIR/runtime_lib_empty.log" "L0C-0015"

if "$STAGE2_L0C" --build -P "$(native_path "$FIXTURE_ROOT")" no_main >"$WORK_DIR/no_main.log" 2>&1; then
    fail "expected missing-main build to fail"
fi
assert_contains "$WORK_DIR/no_main.log" "L0C-0012"

"$STAGE2_L0C" --build --keep-c -P "$(native_path "$FIXTURE_ROOT")" -o "$(native_path "$BYTE_MAIN_BIN")" byte_main >"$WORK_DIR/byte_main.log" 2>&1
assert_contains "$WORK_DIR/byte_main.log" "L0C-0013"
assert_file "$BYTE_MAIN_BIN"
assert_file "${BYTE_MAIN_BIN%.*}.c"

echo "l0c_build_run_test: PASS"
