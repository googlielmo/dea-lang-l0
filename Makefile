.DEFAULT_GOAL := help

PYTHON ?= python3
DIST_DIR ?= dist

.PHONY: \
	help \
	venv \
	install-dev-stage1 \
	install-dev-stage2 \
	install-dev-stages \
	use-dev-stage1 \
	use-dev-stage2 \
	test-stage1 \
	test-stage2 \
	test-stage2-trace \
	triple-test \
	test-all \
	docs \
	docs-pdf \
	clean \
	clean-dist

help:
	@printf '%s\n' \
		'L0 repo-local dist workflow' \
		'' \
		'Targets:' \
		'  help               Show this help text.' \
		'  venv               Create the local `.venv` (prefer `uv`, fall back to `python -m venv`).' \
		'  install-dev-stage1 Install the repo-local Stage 1 launcher and environment script.' \
		'  install-dev-stage2 Build and install the repo-local Stage 2 launcher.' \
		'  install-dev-stages Prepare both Stage 1 and Stage 2 launchers under DIST_DIR.' \
		'  use-dev-stage1     Switch the repo-local `l0c` alias to Stage 1.' \
		'  use-dev-stage2     Switch the repo-local `l0c` alias to Stage 2.' \
		'  test-stage1        Validate the Stage 1 Python compiler test suite.' \
		'  test-stage2        Validate the Stage 2 compiler test suite, including triple-bootstrap.' \
		'  test-stage2-trace  Validate Stage 2 ARC and memory tracing behavior.' \
		'  test-all           Run the full Stage 1 and Stage 2 validation suite.' \
		'  triple-test        Run the Stage 2 triple-bootstrap check on its own.' \
		'  docs               Generate the project documentation.' \
		'  docs-pdf           Generate the project documentation, including the PDF manual.' \
		'  clean              Remove repo-local build artifacts under `build/*`, Stage 2 test `.tmp*` files, and default executables.' \
		'  clean-dist         Remove the repo-local dist tree (override with `DIST_DIR`, see below).' \
		'' \
		'Variables:' \
		'  DIST_DIR=dist      Repo-local output root. Must stay inside the repository.' \
		'                     Example: make DIST_DIR=./dev-dist install-dev-stages'

venv:
	@if [ -x ./.venv/bin/python ]; then \
		printf '%s\n' 'make venv: reusing existing .venv'; \
	elif command -v uv >/dev/null 2>&1; then \
		uv sync --group dev; \
	else \
		$(PYTHON) -m venv .venv; \
		./.venv/bin/python -m pip install -e . "pytest>=9.0.2" "pytest-xdist>=3.5"; \
	fi

install-dev-stage1:
	$(PYTHON) ./scripts/gen_dist_tools.py write-stage1-wrapper --dist-dir "$(DIST_DIR)"
	$(PYTHON) ./scripts/gen_dist_tools.py write-env-script --dist-dir "$(DIST_DIR)"

install-dev-stage2:
	DIST_DIR="$(DIST_DIR)" ./scripts/build-stage2-l0c.sh
	$(PYTHON) ./scripts/gen_dist_tools.py write-env-script --dist-dir "$(DIST_DIR)"

install-dev-stages: install-dev-stage1 install-dev-stage2

use-dev-stage1: install-dev-stage1
	$(PYTHON) ./scripts/gen_dist_tools.py set-alias --dist-dir "$(DIST_DIR)" --stage stage1
	@printf '\n------------------------------------------------------------------------------\n'
	@printf 'To activate the selected l0c stage in this shell execute:\n\n    source %s/bin/l0-env.sh\n\nThis adds %s/bin to your current PATH, so `l0c` invokes the selected compiler. See README.md for more information.' "$(DIST_DIR)" "$(DIST_DIR)"
	@printf '\n------------------------------------------------------------------------------\n'

use-dev-stage2: install-dev-stage2
	$(PYTHON) ./scripts/gen_dist_tools.py set-alias --dist-dir "$(DIST_DIR)" --stage stage2
	@printf '\n------------------------------------------------------------------------------\n'
	@printf 'To activate the selected l0c stage in this shell execute:\n\n    source %s/bin/l0-env.sh\n\nThis adds %s/bin to your current PATH, so `l0c` invokes the selected compiler. See README.md for more information.' "$(DIST_DIR)" "$(DIST_DIR)"
	@printf '\n------------------------------------------------------------------------------\n'

test-stage1: venv
	./.venv/bin/python -m pytest -n auto

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
	rm -f ./a.out ./a.exe
	rm -f ./compiler/stage2_l0/a.out ./compiler/stage2_l0/a.exe
	rm -f ./compiler/stage2_l0/tests/.tmp*

clean-dist:
	$(PYTHON) ./scripts/gen_dist_tools.py clean-dist --dist-dir "$(DIST_DIR)"
