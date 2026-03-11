.DEFAULT_GOAL := help

PYTHON ?= python3
DIST_DIR ?= dist

.PHONY: \
	help \
	install-stage1 \
	install-stage2 \
	install-all \
	use-stage1 \
	use-stage2 \
	test-stage1 \
	test-stage2 \
	test-stage2-trace \
	triple-test \
	test-all \
	docs \
	docs-pdf \
	clean-dist

help:
	@printf '%s\n' \
		'L0 repo-local dist workflow' \
		'' \
		'Targets:' \
		'  help               Show this help text.' \
		'  install-stage1     Write `bin/l0c-stage1` and `bin/l0-env.sh` under DIST_DIR.' \
		'  install-stage2     Build Stage 2 into DIST_DIR and refresh `bin/l0-env.sh`.' \
		'  install-all        Install both stage-specific commands without changing `bin/l0c`.' \
		'  use-stage1         Point `bin/l0c` at `bin/l0c-stage1` and print the source command.' \
		'  use-stage2         Point `bin/l0c` at `bin/l0c-stage2` and print the source command.' \
		'  test-stage1        Run `pytest -n auto`.' \
		'  test-stage2        Run `./compiler/stage2_l0/run_tests.py`.' \
		'  test-stage2-trace  Run `./compiler/stage2_l0/run_trace_tests.py`.' \
		'  test-all           Run the three test targets above.' \
		'  triple-test        Run `./compiler/stage2_l0/tests/l0c_triple_bootstrap_test.py` only.' \
		'  docs               Run `./scripts/gen-docs.sh`.' \
		'  docs-pdf           Run `./scripts/gen-docs.sh --pdf`.' \
		'  clean			  Remove all generated docs and temp files under ./build' \
		'  clean-dist         Remove the validated DIST_DIR tree.' \
		'' \
		'Variables:' \
		'  DIST_DIR=dist      Repo-local output root. Must stay inside the repository.' \
		'                     Example: make DIST_DIR=./dev-dist install-all'

install-stage1:
	$(PYTHON) ./scripts/gen_dist_tools.py write-stage1-wrapper --dist-dir "$(DIST_DIR)"
	$(PYTHON) ./scripts/gen_dist_tools.py write-env-script --dist-dir "$(DIST_DIR)"

install-stage2:
	DIST_DIR="$(DIST_DIR)" ./scripts/build-stage2-l0c.sh
	$(PYTHON) ./scripts/gen_dist_tools.py write-env-script --dist-dir "$(DIST_DIR)"

install-all: install-stage1 install-stage2

use-stage1: install-stage1
	$(PYTHON) ./scripts/gen_dist_tools.py set-alias --dist-dir "$(DIST_DIR)" --stage stage1
	@printf 'source %s/bin/l0-env.sh\n' "$(DIST_DIR)"

use-stage2: install-stage2
	$(PYTHON) ./scripts/gen_dist_tools.py set-alias --dist-dir "$(DIST_DIR)" --stage stage2
	@printf 'source %s/bin/l0-env.sh\n' "$(DIST_DIR)"

test-stage1:
	pytest -n auto

test-stage2:
	./compiler/stage2_l0/run_tests.py

test-stage2-trace:
	./compiler/stage2_l0/run_trace_tests.py

test-all: test-stage1 test-stage2 test-stage2-trace

triple-test:
	$(PYTHON) ./compiler/stage2_l0/tests/l0c_triple_bootstrap_test.py

docs:
	./scripts/gen-docs.sh

docs-pdf:
	./scripts/gen-docs.sh --pdf

clean:
	rm -rf ./build/*

clean-dist:
	$(PYTHON) ./scripts/gen_dist_tools.py clean-dist --dist-dir "$(DIST_DIR)"
