#!/bin/sh

set -eu

repo_root()
{
    CDPATH= cd -- "$(dirname -- "$0")/../.." && pwd
}

ROOT="$(repo_root)"
TOOLING_CONFIG="$ROOT/dev/config/tooling.env"

if [ ! -r "$TOOLING_CONFIG" ]; then
    echo "error: cannot read $TOOLING_CONFIG" >&2
    exit 1
fi

# shellcheck disable=SC1090
. "$TOOLING_CONFIG"

UV_PROJECT="$ROOT/$UV_PROJECT"

require_uv()
{
    if ! command -v uv >/dev/null 2>&1; then
        echo "error: uv is required but was not found in PATH" >&2
        exit 1
    fi
}

uv_run()
{
    require_uv

    uv run \
        --project "$UV_PROJECT" \
        --python "$PYTHON_VERSION" \
        --frozen \
        "$@"
}
