.DEFAULT_GOAL := help

VENV_DIR_REL := ../.venv
VENV_DIR := $(abspath $(VENV_DIR_REL))

ifeq ($(OS),Windows_NT)
VENV_PYTHON_DEFAULT := $(VENV_DIR)/Scripts/python.exe
else
VENV_PYTHON_DEFAULT := $(VENV_DIR)/bin/python
endif

HOST_PYTHON ?= $(shell if command -v python3 >/dev/null 2>&1; then printf '%s' python3; else printf '%s' python; fi)
VENV_PYTHON := $(shell if [ -x "$(VENV_DIR)/bin/python" ]; then printf '%s' "$(VENV_DIR)/bin/python"; elif [ -x "$(VENV_DIR)/Scripts/python.exe" ]; then printf '%s' "$(VENV_DIR)/Scripts/python.exe"; else printf '%s' $(VENV_PYTHON_DEFAULT); fi)
PYTHON ?= $(shell if [ -x "$(VENV_DIR)/bin/python" ]; then printf '%s' "$(VENV_DIR)/bin/python"; elif [ -x "$(VENV_DIR)/Scripts/python.exe" ]; then printf '%s' "$(VENV_DIR)/Scripts/python.exe"; else printf '%s' $(HOST_PYTHON); fi)
L1_BUILD_DIR ?= build/dea
DOCKER_IMAGE ?= l1-test
VENV_UV_FLAGS := --quiet
VENV_PIP_FLAGS := --quiet --disable-pip-version-check
VENV_QUIET_LABEL := (quiet)

PIP_DEPS_CMD = import tomllib,pathlib;\
	g=tomllib.loads(pathlib.Path('pyproject.toml').read_text()).get('dependency-groups',{});\
	print(' '.join(d for d in g.get('dev',[])+g.get('docs',[]) if isinstance(d,str)))

.PHONY: help _check-python venv _ensure-bootstrap-l0-stage2 build-stage1 use-dev-stage1 test-stage1 test-all print-l1-build-dir clean docker

help:
	@printf '%s\n' \
		'Dea/L1 bootstrap workflow' \
		'' \
		'Targets:' \
		'  venv               Create or reuse the shared monorepo `../.venv`.' \
		'  use-dev-stage1     Build and switch the repo-local `l1c` alias to Stage 1.' \
		'  test-all           Run the full L1 validation suite (currently `test-stage1` only).' \
		'  test-stage1        Run the L1 Stage 1 `.l0` implementation tests with the built repo-local compiler.' \
		'  clean              Remove repo-local build artifacts under `build/*`.' \
		'' \
		'Docker:' \
		'  docker             Explicitly run a target in the repo-owned Linux Docker container (CMD=<target>).' \
		'' \
		'Variables:' \
		'  L1_BUILD_DIR=build/dea' \
		'                     Repo-local L1 build root.' \
		'  L1_BOOTSTRAP_L0C=<path>' \
		'                     Explicit upstream L0 Stage 2 compiler wrapper or native binary.' \
		'  TESTS=""' \
		'                     Optional Stage 1 test names for `test-stage1`.' \
		'  DOCKER_IMAGE=l1-test' \
		'                     Docker image tag used by `make docker`.' \
		'  DOCKER_L0_CC=<compiler>' \
		'                     Optional upstream L0 C compiler passed into the Docker run as `L0_CC` (`gcc` or `clang`).' \
		'' \
		'Default local bootstrap flow:' \
		'  1. `make use-dev-stage1`  # auto-prepares ../l0 Stage 2 if needed' \
		'  2. `source build/dea/bin/l1-env.sh`' \
		'  3. `l1c --help`'

_check-python:
	@$(PYTHON) -c "import sys; sys.exit(0 if sys.version_info >= (3, 14) else 1)" 2>/dev/null \
		|| { printf 'error: Python 3.14+ is required (found: %s)\n' \
			"$$($(PYTHON) -c 'import sys; print(".".join(map(str,sys.version_info[:3])))' 2>/dev/null || echo 'none')" >&2; exit 1; }

venv: _check-python
	@if command -v uv >/dev/null 2>&1; then \
		if [ -x "$(VENV_PYTHON)" ]; then \
			printf '%s\n' 'make venv: syncing existing ../.venv with uv $(VENV_QUIET_LABEL)'; \
		fi; \
		UV_PROJECT_ENVIRONMENT="$(VENV_DIR)" uv sync $(VENV_UV_FLAGS) --group dev --group docs; \
	elif [ -x "$(VENV_PYTHON)" ]; then \
		printf '%s\n' 'make venv: refreshing existing ../.venv with pip $(VENV_QUIET_LABEL)'; \
		"$(VENV_PYTHON)" -m pip install $(VENV_PIP_FLAGS) $$("$(VENV_PYTHON)" -c "$(PIP_DEPS_CMD)"); \
	else \
		$(PYTHON) -m venv "$(VENV_DIR)"; \
		_vp="$$(if [ -x "$(VENV_DIR)/bin/python" ]; then printf '%s' "$(VENV_DIR)/bin/python"; else printf '%s' "$(VENV_DIR)/Scripts/python.exe"; fi)"; \
		"$$_vp" -m pip install $(VENV_PIP_FLAGS) $$("$$_vp" -c "$(PIP_DEPS_CMD)"); \
	fi

_ensure-bootstrap-l0-stage2:
	@if [ -n "$${L1_BOOTSTRAP_L0C:-}" ]; then \
		printf '%s\n' 'make build-stage1: using explicit L1_BOOTSTRAP_L0C override'; \
	elif [ -x ../l0/build/dea/bin/l0c-stage2 ] || [ -x ../l0/build/dea/bin/l0c-stage2.cmd ]; then \
		:; \
	else \
		printf '%s\n' 'make build-stage1: preparing repo-local upstream L0 Stage 2 compiler'; \
		$(MAKE) -C ../l0 use-dev-stage2; \
	fi
	@if [ -z "$${L1_BOOTSTRAP_L0C:-}" ] && [ ! -x ../l0/build/dea/bin/l0c-stage2 ] && [ ! -x ../l0/build/dea/bin/l0c-stage2.cmd ]; then \
		printf '%s\n' 'make build-stage1: missing repo-local upstream compiler at ../l0/build/dea/bin/l0c-stage2 after bootstrap preparation' >&2; \
		exit 1; \
	fi

build-stage1: venv _ensure-bootstrap-l0-stage2
	L1_BUILD_DIR="$(L1_BUILD_DIR)" "$(PYTHON)" ./scripts/build_stage1_l1c.py
	@printf 'Repo-local L1 Stage 1 compiler version:\n'
	@"$(L1_BUILD_DIR)/bin/l1c-stage1" --version

use-dev-stage1: build-stage1
	@printf '\n------------------------------------------------------------------------------\n'
ifeq ($(OS),Windows_NT)
	@cmd_env_path="$$(cygpath -w "$$(realpath "$(L1_BUILD_DIR)/bin/l1-env.cmd")")"; \
		printf 'To activate the selected l1c stage in this shell:\n\nIn an MSYS2 bash shell:\n\n    source %s/bin/l1-env.sh\n\nIn CMD:\n\n    call "%s"\n\nThen run:\n\n    l1c --help\n\nSee ../README-WINDOWS.md for PowerShell and direct-launcher guidance.' "$(L1_BUILD_DIR)" "$$cmd_env_path"
else
	@printf 'To activate the selected l1c stage in this shell, run:\n\n    source %s/bin/l1-env.sh\n\nThis adds %s/bin to your current PATH, so `l1c` invokes the selected compiler. See README.md for more information.' "$(L1_BUILD_DIR)" "$(L1_BUILD_DIR)"
endif
	@printf '\n------------------------------------------------------------------------------\n'

test-stage1: venv build-stage1
	L1_BUILD_DIR="$(L1_BUILD_DIR)" "$(VENV_PYTHON)" ./compiler/stage1_l0/scripts/run_tests.py $(TESTS)

test-all: test-stage1

print-l1-build-dir:
	@printf '%s\n' "$(L1_BUILD_DIR)"

clean:
	rm -rf ./build/*
	rm -f ./a.out ./a.exe
	rm -f ./compiler/stage1_l0/a.out ./compiler/stage1_l0/a.exe
	rm -f ./compiler/stage1_l0/tests/.tmp*

docker:
	@if [ -z "$(CMD)" ]; then \
		echo "Usage: make docker CMD=<target>"; \
		echo "Example: make docker CMD=test-all"; \
		exit 2; \
	else \
		docker build -f Dockerfile -t "$(DOCKER_IMAGE)" .. && docker run --rm $(if $(strip $(DOCKER_L0_CC)),-e L0_CC=$(DOCKER_L0_CC)) "$(DOCKER_IMAGE)" make $(CMD); \
	fi
