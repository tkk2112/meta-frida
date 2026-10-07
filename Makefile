include dev/config/tooling.env

UV_RUN := uv run \
	--project $(UV_PROJECT) \
	--python $(PYTHON_VERSION) \
	--frozen

UV_SYNC := uv sync \
	--project $(UV_PROJECT) \
	--python $(PYTHON_VERSION)

PYTHON_SCRIPTS := \
	dev/scripts/update_frida.py

OELINT := $(UV_RUN) oelint-adv --quiet --release $(OELINT_RELEASE)

OELINT_FORMAT := $(OELINT) \
	--rulefile dev/config/oelint-format.json \
	--jobs=1 \
	--fix \
	--nobackup

OELINT_FILES := $(shell find recipes-frida recipes-devtools classes-recipe conf \
	-type f \( -name '*.bb' -o -name '*.bbappend' -o -name '*.bbclass' -o -name '*.inc' \))

.PHONY: format check-format lint sync

format:
	$(OELINT_FORMAT) $(OELINT_FILES)
	$(UV_RUN) ruff format $(PYTHON_SCRIPTS)

check-format:
	$(OELINT_FORMAT) $(OELINT_FILES)
	git diff --exit-code
	$(UV_RUN) ruff format --check $(PYTHON_SCRIPTS)

lint:
	$(OELINT) $(OELINT_FILES)
	$(UV_RUN) ruff check $(PYTHON_SCRIPTS)
	$(UV_RUN) ty check $(PYTHON_SCRIPTS)

sync:
	$(UV_SYNC) --upgrade
