include dev/config/tooling.env

UV_RUN := uv run \
	--project $(UV_PROJECT) \
	--python $(PYTHON_VERSION) \
	--frozen

UV_SYNC := uv sync \
	--project $(UV_PROJECT) \
	--python $(PYTHON_VERSION)

PYTHON_SCRIPTS_HOST := \
	dev/scripts/update_frida.py \
	$(wildcard dev/scripts/tests/test_*.py)

PYTHON_SCRIPTS := \
	$(PYTHON_SCRIPTS_HOST) \
	$(wildcard lib/oeqa/runtime/cases/*.py)

OELINT := OELINT_CONFIG=$(OELINT_CONFIG) $(UV_RUN) oelint-adv \
	--release $(OELINT_RELEASE) \
	--constantmod=+oelint.constants.json

OELINT_FORMAT_CHECK := $(OELINT) \
	--rulefile oelint-format.json \
	--jobs=1

OELINT_FORMAT := $(OELINT_FORMAT_CHECK) \
	--fix \
	--nobackup

OELINT_FILES := $(shell find \
	recipes-frida recipes-devtools recipes-test classes-recipe conf \
	-type f \( -name '*.bb' -o -name '*.bbappend' -o -name '*.bbclass' -o -name '*.inc' \))

.PHONY: \
	format check-format lint sync \
	test test-unit test-lock test-vala test-target test-sdk

format:
	$(OELINT_FORMAT) $(OELINT_FILES)
	$(UV_RUN) ruff format $(PYTHON_SCRIPTS)

check-format:
	$(OELINT_FORMAT_CHECK) $(OELINT_FILES)
	$(UV_RUN) ruff format --check $(PYTHON_SCRIPTS)


lint:
	@printf '=== BitBake recipes and classes: oelint ===\n'
	$(OELINT) $(OELINT_FILES)
	@printf '=== Python: Ruff ===\n'
	$(UV_RUN) ruff check $(PYTHON_SCRIPTS)
	@printf '=== Python: ty ===\n'
	$(UV_RUN) ty check $(PYTHON_SCRIPTS_HOST)
	@printf '=== Lint PASSED ===\n'

sync:
	$(UV_SYNC) --upgrade

test-unit:
	$(UV_RUN) pytest -v dev/scripts/tests

test-lock:
	@$(SCRIPTS_DIR)/update-frida --check

test-vala:
	@$(SCRIPTS_DIR)/bitbake -q -c smoketest frida-vala-smoketest-native
	@printf 'RESULTS - Frida Vala smoke test: PASSED\n'

test-target:
	@$(SCRIPTS_DIR)/smoketest --all

test-sdk:
	@$(SCRIPTS_DIR)/yocto shell dev/kas/sdk.yml -c '\
		set -eu; \
		echo "=== Verify SDK dependency compatibility ==="; \
		python3 /repo/dev/scripts/update_frida.py --check-tools --bitbake; \
		echo "=== Build SDK ==="; \
		bitbake core-image-minimal -c populate_sdk; \
		echo "=== Run installed SDK smoke test ==="; \
		sh /repo/tests/sdk/smoke.sh; \
	'

test:
	@$(MAKE) check-format
	@$(MAKE) lint
	@$(MAKE) test-unit
	@$(MAKE) test-lock
	@$(MAKE) test-vala
	@$(MAKE) test-target
	@$(MAKE) test-sdk
	@printf '\nRESULTS - All meta-frida tests PASSED\n'
