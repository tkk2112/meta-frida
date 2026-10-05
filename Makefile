PYTHON_SCRIPTS := \
	dev/scripts/update-frida

OELINT := oelint-adv --quiet --release wrynose

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
	uv run ruff format $(PYTHON_SCRIPTS)

check-format:
	$(OELINT_FORMAT) $(OELINT_FILES)
	git diff --exit-code
	uv run ruff format --check $(PYTHON_SCRIPTS)

lint:
	$(OELINT) $(OELINT_FILES)
	uv run ruff check $(PYTHON_SCRIPTS)
	uv run ty check $(PYTHON_SCRIPTS)

sync:
	UV_FROZEN=0 uv sync --upgrade
