#!/bin/bash
# Run all tests in compiler/stage2_l0/tests/

set -e

VERBOSE=0

if [ "$1" == "-v" ]; then
    VERBOSE=1
fi

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"
TESTS_DIR="$SCRIPT_DIR/tests"

cd "$REPO_ROOT"

passed=0
failed=0
failed_tests=""

echo "Running stage2_l0 tests..."
echo "======================================"

for test_file in "$TESTS_DIR"/*.l0; do
    test_name=$(basename "$test_file" .l0)
    echo -n "Running $test_name... "

    # if VERBOSE is set, show output immediately
    if [ $VERBOSE -eq 1 ]; then
        echo
        if ./l0c -P compiler/stage2_l0/src run "$test_file"; then
            echo "PASS"
            ((passed++))
        else
            echo "FAIL"
            ((failed++))
            failed_tests="$failed_tests $test_name"
        fi
        continue
    else
        # otherwise, capture output to a temp file
      if ./l0c -P compiler/stage2_l0/src run "$test_file" > /tmp/test_output_$$.txt 2>&1; then
          echo "PASS"
          ((passed++))
      else
          echo "FAIL"
          ((failed++))
          failed_tests="$failed_tests $test_name"
      fi
    fi
done

if [ $VERBOSE -eq 0 ] && [ $failed -gt 0 ]; then
    echo "======================================"
    echo "Failed test outputs:"
    for test_file in $failed_tests; do
        echo "Output for $test_file:"
        cat /tmp/test_output_$$.txt
        echo "--------------------------------------"
    done
fi

rm -f /tmp/test_output_$$.txt

echo "======================================"
echo "Passed: $passed"
echo "Failed: $failed"

if [ $failed -gt 0 ]; then
    echo "Failed tests:$failed_tests"
    exit 1
else
    echo "All tests passed!"
    exit 0
fi
