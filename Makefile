.DEFAULT_GOAL := help

ifeq ($(OS),Windows_NT)
VENV_PYTHON_DEFAULT := ./.venv/Scripts/python.exe
else
VENV_PYTHON_DEFAULT := ./.venv/bin/python
endif

HOST_PYTHON ?= $(shell if command -v python3 >/dev/null 2>&1; then printf '%s' python3; else printf '%s' python; fi)
VENV_PYTHON := $(shell if [ -x ./.venv/bin/python ]; then printf '%s' ./.venv/bin/python; elif [ -x ./.venv/Scripts/python.exe ]; then printf '%s' ./.venv/Scripts/python.exe; else printf '%s' $(VENV_PYTHON_DEFAULT); fi)
PYTHON ?= $(shell if [ -x ./.venv/bin/python ]; then printf '%s' ./.venv/bin/python; elif [ -x ./.venv/Scripts/python.exe ]; then printf '%s' ./.venv/Scripts/python.exe; else printf '%s' $(HOST_PYTHON); fi)
DEA_BUILD_DIR ?= build/dea
DOCKER_IMAGE ?= l0-test

.PHONY: \
	help \
	venv \
	install-dev-stage1 \
	install-dev-stage2 \
	install-dev-stages \
	install \
	dist \
	use-dev-stage1 \
	use-dev-stage2 \
	test-stage1 \
	test-stage2 \
	test-stage2-trace \
	test-dist \
	triple-test \
	test-all \
	print-dea-build-dir \
	docs \
	docs-pdf \
	clean \
	clean-dea-build

help:
	@printf '%s\n' \
		'Dea/L0 installation and development workflow' \
		'' \
		'Targets:' \
		'  install            Install the self-hosted Stage 2 compiler under PREFIX.' \
		'  dist               Build a relocatable Stage 2 `dist/` tree under `build/` and archive it.' \
		'' \
		'Development targets:' \
		'  venv               Create the local `.venv` (prefer `uv`, fall back to `python -m venv`).' \
		'  install-dev-stages Prepare both Stage 1 and Stage 2 launchers under DEA_BUILD_DIR.' \
		'  install-dev-stage1 Install the repo-local Stage 1 launcher and environment script.' \
		'  install-dev-stage2 Build and install the repo-local Stage 2 launcher.' \
		'  use-dev-stage1     Switch the repo-local `l0c` alias to Stage 1.' \
		'  use-dev-stage2     Switch the repo-local `l0c` alias to Stage 2.' \
		'  test-all           Run the full Stage 1, Stage 2, and distribution validation suite.' \
		'  test-stage1        Validate the Stage 1 Python compiler test suite.' \
		'  test-stage2        Validate the Stage 2 compiler test suite; pass TESTS="name1 name2" to run selected cases.' \
		'  test-stage2-trace  Validate Stage 2 ARC and memory tracing behavior.' \
		'  test-dist          Validate the `make dist` packaging workflow end to end.' \
		'  triple-test        Run the Stage 2 triple-bootstrap check on its own.' \
		'' \
		'Docker:' \
		'  docker             Explicitly run a target in the repo-owned Linux Docker container (CMD=<target>).' \
		'' \
		'Documentation targets:' \
		'  docs               Generate the project documentation.' \
		'  docs-pdf           Generate the project documentation, including the PDF manual.' \
		'' \
		'Other targets:' \
		'  help               Show this help text.' \
		'  clean              Remove all repo-local build artifacts under `build/*` (including temporary `dist` trees and archives), temporary test files, and default executables.' \
		'  clean-dea-build    Remove the repo-local Dea build tree (override with `DEA_BUILD_DIR`, see below).' \
		'' \
		'Variables:' \
		'  PREFIX=<required>  Install prefix for `install`.' \
		'                     Example: make PREFIX=/opt/dea install' \
		'  DEA_BUILD_DIR=build/dea' \
		'                     Repo-local build root. Must stay inside the repository.' \
		'                     Example: make DEA_BUILD_DIR=build/dev-dea install-dev-stages' \
		'  TESTS=""' \
		'                     Optional Stage 2 test names for `test-stage2`; blank runs the full suite.' \
		'                     Example: make test-stage2 TESTS="driver_test l0c_build_run_test"' \
		'  DOCKER_IMAGE=l0-test' \
		'                     Docker image tag used by `make docker`.' \
		'  DOCKER_L0_CC=<compiler>' \
		'                     Optional C compiler passed into the Docker run as `L0_CC` (`gcc` or `clang`).'

venv:
	@if command -v uv >/dev/null 2>&1; then \
		if [ -x "$(VENV_PYTHON)" ]; then \
			printf '%s\n' 'make venv: syncing existing .venv with uv'; \
		fi; \
		uv sync --group dev --group docs; \
	elif [ -x "$(VENV_PYTHON)" ]; then \
		printf '%s\n' 'make venv: refreshing existing .venv with pip'; \
		"$(VENV_PYTHON)" -m pip install -e . "pytest>=9.0.2" "pytest-xdist>=3.5" "jinja2>=3.1.6" "PyYAML>=6.0.2" "pygments>=2.19.2"; \
	else \
		$(PYTHON) -m venv .venv; \
		"$(VENV_PYTHON)" -m pip install -e . "pytest>=9.0.2" "pytest-xdist>=3.5" "jinja2>=3.1.6" "PyYAML>=6.0.2" "pygments>=2.19.2"; \
	fi

install-dev-stage1:
	$(PYTHON) ./scripts/gen_dist_tools.py write-stage1-wrapper --dea-build-dir "$(DEA_BUILD_DIR)"
	$(PYTHON) ./scripts/gen_dist_tools.py write-env-script --dea-build-dir "$(DEA_BUILD_DIR)"
	@printf 'Repo-local Stage 1 compiler version:\n'
	@"$(DEA_BUILD_DIR)/bin/l0c-stage1" --version

install-dev-stage2:
	DEA_BUILD_DIR="$(DEA_BUILD_DIR)" ./scripts/build-stage2-l0c.sh
	$(PYTHON) ./scripts/gen_dist_tools.py write-env-script --dea-build-dir "$(DEA_BUILD_DIR)"
	@printf 'Repo-local Stage 2 compiler version:\n'
	@"$(DEA_BUILD_DIR)/bin/l0c-stage2" --version

install-dev-stages: install-dev-stage1 install-dev-stage2

install:
	@if [ -z "$(strip $(PREFIX))" ]; then \
		printf '%s\n' 'make install: PREFIX is required; example: make PREFIX=/tmp/l0-install L0_CC=gcc install' >&2; \
		exit 2; \
	fi
	$(PYTHON) ./scripts/gen_dist_tools.py install-prefix --prefix "$(PREFIX)"
	@printf 'Installed Stage 2 compiler version:\n'
	@"$(PREFIX)/bin/l0c-stage2" --version
	@printf '\n------------------------------------------------------------------------------\n'
ifeq ($(OS),Windows_NT)
	@printf 'Dea/L0 compiler installed at %s/bin/l0c.\nTo add the installed compiler to your current PATH:\n\nIn an MSYS2 bash shell:\n\n    source %s/bin/l0-env.sh\n\nIn CMD:\n\n    set "PATH=%s\\bin;%%PATH%%"\n\nSee README.md for more information.' "$(PREFIX)" "$(PREFIX)" "$(PREFIX)"
else
	@printf 'Dea/L0 compiler installed at %s/bin/l0c.\nTo add the installed compiler to your current PATH in this shell, run:\n\n    source %s/bin/l0-env.sh\n\nSee README.md for more information.' "$(PREFIX)" "$(PREFIX)"
endif
	@printf '\n------------------------------------------------------------------------------\n'

dist: venv
	$(PYTHON) ./scripts/gen_dist_tools.py make-dist

use-dev-stage1: install-dev-stage1
	$(PYTHON) ./scripts/gen_dist_tools.py set-alias --dea-build-dir "$(DEA_BUILD_DIR)" --stage stage1
	@printf '\n------------------------------------------------------------------------------\n'
ifeq ($(OS),Windows_NT)
	@printf 'To use the repo-local Stage 1 compiler on Windows:\n\nIn an MSYS2 bash shell:\n\n    source %s/bin/l0-env.sh\n\nIn CMD:\n\n    %%cd%%\\scripts\\l0c.cmd --help\n\nIn PowerShell:\n\n    & "$$PWD\\scripts\\l0c.cmd" --help\n\nThe repo-local `l0c` alias under %s/bin is Bash-only for Stage 1 today. Use `scripts\\l0c.cmd` in native Windows shells. See README-WINDOWS.md for more information.' "$(DEA_BUILD_DIR)" "$(DEA_BUILD_DIR)"
else
	@printf 'To activate the selected l0c stage in this shell, run:\n\n    source %s/bin/l0-env.sh\n\nThis adds %s/bin to your current PATH, so `l0c` invokes the selected compiler. See README.md for more information.' "$(DEA_BUILD_DIR)" "$(DEA_BUILD_DIR)"
endif
	@printf '\n------------------------------------------------------------------------------\n'

use-dev-stage2: install-dev-stage2
	$(PYTHON) ./scripts/gen_dist_tools.py set-alias --dea-build-dir "$(DEA_BUILD_DIR)" --stage stage2
	@printf '\n------------------------------------------------------------------------------\n'
ifeq ($(OS),Windows_NT)
	@printf 'To activate the selected l0c stage in this shell:\n\nIn an MSYS2 bash shell:\n\n    source %s/bin/l0-env.sh\n\nIn CMD:\n\n    set "PATH=%%cd%%\\%s\\bin;%%PATH%%"\n\nThis adds %s/bin to your current PATH, so `l0c` invokes the selected compiler. See README.md for more information.' "$(DEA_BUILD_DIR)" "$(DEA_BUILD_DIR)" "$(DEA_BUILD_DIR)"
else
	@printf 'To activate the selected l0c stage in this shell, run:\n\n    source %s/bin/l0-env.sh\n\nThis adds %s/bin to your current PATH, so `l0c` invokes the selected compiler. See README.md for more information.' "$(DEA_BUILD_DIR)" "$(DEA_BUILD_DIR)"
endif
	@printf '\n------------------------------------------------------------------------------\n'

test-stage1: venv
	"$(VENV_PYTHON)" -m pytest -n auto

test-stage2: venv install-dev-stage2
	DEA_BUILD_DIR="$(DEA_BUILD_DIR)" "$(VENV_PYTHON)" ./compiler/stage2_l0/run_tests.py $(TESTS)

test-stage2-trace: venv install-dev-stage2
	DEA_BUILD_DIR="$(DEA_BUILD_DIR)" "$(VENV_PYTHON)" ./compiler/stage2_l0/run_trace_tests.py

test-dist: venv
	"$(VENV_PYTHON)" ./tests/test_make_dist_workflow.py

test-all: test-stage1 test-stage2 test-stage2-trace test-dist

triple-test: venv install-dev-stage2
	DEA_BUILD_DIR="$(DEA_BUILD_DIR)" "$(VENV_PYTHON)" ./compiler/stage2_l0/tests/l0c_triple_bootstrap_test.py

print-dea-build-dir:
	@printf '%s\n' "$(DEA_BUILD_DIR)"

docs:
	./scripts/gen-docs.sh --strict

docs-pdf:
	./scripts/gen-docs.sh --strict --pdf

clean:
	rm -rf ./build/*
	rm -f ./a.out ./a.exe
	rm -f ./compiler/stage2_l0/a.out ./compiler/stage2_l0/a.exe
	rm -f ./compiler/stage2_l0/tests/.tmp*

clean-dea-build:
	$(PYTHON) ./scripts/gen_dist_tools.py clean-dea-build --dea-build-dir "$(DEA_BUILD_DIR)"

docker:
	@if [ -z "$(CMD)" ]; then \
		echo "Usage: make docker CMD=<target>"; \
		echo "Example: make docker CMD=test-all"; \
		exit 2; \
	else \
		docker build -t "$(DOCKER_IMAGE)" . && docker run --rm $(if $(strip $(DOCKER_L0_CC)),-e L0_CC=$(DOCKER_L0_CC)) "$(DOCKER_IMAGE)" make $(CMD); \
	fi
