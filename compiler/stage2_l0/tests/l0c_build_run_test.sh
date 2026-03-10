#!/bin/bash
#
# SPDX-License-Identifier: MIT OR Apache-2.0
# Copyright (c) 2026 gwz
#

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/../../.." && pwd)"
FIXTURE_ROOT="$SCRIPT_DIR/fixtures/driver"
WORK_DIR="$(mktemp -d /tmp/l0_stage2_build_run_test.XXXXXX)"
BOOTSTRAP_PARENT="$REPO_ROOT/build/tests"
BOOTSTRAP_DIR=""

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
DIST_DIR="${BOOTSTRAP_DIR#$REPO_ROOT/}" ./scripts/build-stage2-l0c.sh >/dev/null
STAGE2_L0C="$BOOTSTRAP_DIR/bin/l0c-stage2"
STAGE2_NATIVE="$BOOTSTRAP_DIR/bin/l0c-stage2.native"

"$STAGE2_L0C" --build --keep-c -P "$FIXTURE_ROOT" -o "$WORK_DIR/ok_main.bin" ok_main >"$WORK_DIR/build_ok.log" 2>&1
assert_file "$WORK_DIR/ok_main.bin"
assert_file "$WORK_DIR/ok_main.c"
"$WORK_DIR/ok_main.bin" >"$WORK_DIR/ok_main.stdout" 2>"$WORK_DIR/ok_main.stderr"
assert_text_equals "$WORK_DIR/ok_main.stdout" ""

"$STAGE2_L0C" --run -P "$FIXTURE_ROOT" argv_dump -- "two words" "rock'n'roll" >"$WORK_DIR/argv.out" 2>&1
cat >"$WORK_DIR/argv.expected" <<'EOF'
3
two words
rock'n'roll
EOF
tail -n 3 "$WORK_DIR/argv.out" >"$WORK_DIR/argv.tail"
diff -u "$WORK_DIR/argv.expected" "$WORK_DIR/argv.tail" >/dev/null || fail "argv forwarding output mismatch"

set +e
"$STAGE2_L0C" --run -P "$FIXTURE_ROOT" exit_seven >"$WORK_DIR/exit_seven.out" 2>&1
rc=$?
set -e
if [ "$rc" -eq 0 ]; then
    fail "expected exit_seven to return a non-zero exit code"
fi
[ "$rc" -eq 7 ] || fail "expected --run exit code 7"

"$STAGE2_L0C" --run --keep-c -P "$FIXTURE_ROOT" -o "$WORK_DIR/kept-name" ok_main >"$WORK_DIR/run_keep.log" 2>&1
assert_file "$WORK_DIR/kept-name.c"

"$STAGE2_L0C" --run -P "$FIXTURE_ROOT" -o "$WORK_DIR/ignored-output" ok_main >"$WORK_DIR/run_warn.log" 2>&1
assert_contains "$WORK_DIR/run_warn.log" "L0C-0017"
assert_no_file "$WORK_DIR/ignored-output"

mkdir "$WORK_DIR/empty-bin"
if env -u L0_CC -u CC PATH="$WORK_DIR/empty-bin" "$STAGE2_NATIVE" --build -P "$FIXTURE_ROOT" ok_main >"$WORK_DIR/no_cc.log" 2>&1; then
    fail "expected no-compiler build to fail"
fi
assert_contains "$WORK_DIR/no_cc.log" "L0C-0009"

if "$STAGE2_L0C" --build --c-compiler false -P "$FIXTURE_ROOT" ok_main >"$WORK_DIR/compile_fail.log" 2>&1; then
    fail "expected explicit failing compiler to fail"
fi
assert_contains "$WORK_DIR/compile_fail.log" "L0C-0010"

if "$STAGE2_L0C" --build --runtime-lib "$WORK_DIR/missing-lib" -P "$FIXTURE_ROOT" ok_main >"$WORK_DIR/runtime_lib_missing.log" 2>&1; then
    fail "expected missing runtime-lib directory to fail"
fi
assert_contains "$WORK_DIR/runtime_lib_missing.log" "L0C-0014"

mkdir "$WORK_DIR/empty-lib"
if "$STAGE2_L0C" --build --runtime-lib "$WORK_DIR/empty-lib" -P "$FIXTURE_ROOT" ok_main >"$WORK_DIR/runtime_lib_empty.log" 2>&1; then
    fail "expected empty runtime-lib directory to fail"
fi
assert_contains "$WORK_DIR/runtime_lib_empty.log" "L0C-0015"

if "$STAGE2_L0C" --build -P "$FIXTURE_ROOT" no_main >"$WORK_DIR/no_main.log" 2>&1; then
    fail "expected missing-main build to fail"
fi
assert_contains "$WORK_DIR/no_main.log" "L0C-0012"

"$STAGE2_L0C" --build --keep-c -P "$FIXTURE_ROOT" -o "$WORK_DIR/byte_main.bin" byte_main >"$WORK_DIR/byte_main.log" 2>&1
assert_contains "$WORK_DIR/byte_main.log" "L0C-0013"
assert_file "$WORK_DIR/byte_main.bin"
assert_file "$WORK_DIR/byte_main.c"

echo "l0c_build_run_test: PASS"
