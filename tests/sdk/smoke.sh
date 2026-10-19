#!/bin/sh
# SPDX-License-Identifier: MIT

set -eu

repo=$(CDPATH= cd -- "$(dirname -- "$0")/../.." && pwd)

FRIDA_EXPECTED_VERSION=$(
    sed -n 's/^FRIDA_VERSION = "\([^"]*\)"$/\1/p' \
        "$repo/conf/include/frida_lock.inc"
)

test -n "$FRIDA_EXPECTED_VERSION"
export FRIDA_EXPECTED_VERSION

: "${BUILDDIR:?Run inside dev/scripts/yocto shell}"

topdir=$(bitbake-getvar --value TOPDIR)
deploy="$topdir/tmp/deploy/sdk"

echo "=== Locate SDK installer ==="

sdk_installer=$(bitbake-getvar -r core-image-minimal --value TOOLCHAIN_OUTPUTNAME)
: "${sdk_installer:?Missing TOOLCHAIN_OUTPUTNAME}"

installer="$deploy/$sdk_installer.sh"

if [ ! -f "$installer" ]; then
    echo "ERROR: SDK installer not found: $installer" >&2
    exit 1
fi

destination=$(mktemp -d /work/frida-sdk-test.XXXXXX)

cleanup() {
    rm -rf "$destination"
}
trap cleanup EXIT HUP INT TERM

echo "Installer: $installer"
echo "Destination: $destination"

echo "=== Install SDK ==="
sh "$installer" -d "$destination" -y

echo "=== Source installed SDK ==="

set -- "$destination"/environment-setup-*
if [ "$#" -ne 1 ] || [ ! -f "$1" ]; then
    echo "Expected one SDK environment setup script" >&2
    exit 1
fi

environment_script=$1

# Yocto SDK environment setup scripts are sourced.
# Preserve their ability to reference optional variables.
set +u
. "$environment_script"
set -u

: "${OECORE_NATIVE_SYSROOT:?SDK native sysroot missing}"

echo "Native sysroot: $OECORE_NATIVE_SYSROOT"
echo "SDK Python: $(command -v python3)"

case "$(command -v python3)" in
    "$OECORE_NATIVE_SYSROOT"/*) ;;
    *)
        echo "ERROR: Python is not from the installed SDK" >&2
        exit 1
        ;;
esac

echo "=== Verify Python bindings and dynamic libraries ==="

python3 - "$OECORE_NATIVE_SYSROOT" <<'PY'
import os
import pathlib
import sys

root = pathlib.Path(sys.argv[1]).resolve()

import frida
import frida._frida
import frida_tools

expected = os.environ.get("FRIDA_EXPECTED_VERSION")
print("Frida version:", frida.__version__)
print("Frida module:", frida.__file__)
print("Frida extension:", frida._frida.__file__)
print("Frida Tools:", frida_tools.__file__)

if frida.__version__ != expected:
    raise SystemExit(
        f"Expected Frida {expected}, got {frida.__version__}"
    )

for module in (frida, frida._frida, frida_tools):
    path = pathlib.Path(module.__file__).resolve()
    if not path.is_relative_to(root):
        raise SystemExit(f"Module outside SDK: {path}")

# Check the libraries the process actually mapped, rather
# than merely assuming RUNPATH implies correct resolution.
maps = pathlib.Path("/proc/self/maps").read_text()
libraries = set()

for line in maps.splitlines():
    fields = line.split()
    if not fields:
        continue
    path = fields[-1]
    if path.startswith("/"):
        libraries.add(path)

for name in (
    "libfrida-core-1.0.so",
    "libglib-2.0.so.0",
    "libgobject-2.0.so.0",
    "libgio-2.0.so.0",
    "libgmodule-2.0.so.0",
):
    matches = sorted(
        path for path in libraries
        if pathlib.Path(path).name == name
        or pathlib.Path(path).name.startswith(name + ".")
    )

    print(f"{name}:")
    for path in matches:
        print(f"  {path}")

    if len(matches) != 1:
        raise SystemExit(
            f"Expected one loaded instance of {name}, got {len(matches)}"
        )

    path = pathlib.Path(matches[0]).resolve()
    if not path.is_relative_to(root):
        raise SystemExit(f"Library outside SDK: {path}")

    if name.startswith("libfrida-core"):
        continue

    private = root / "usr/lib/frida/lib"

    if not path.is_relative_to(private):
        raise SystemExit(f"GLib did not resolve privately: {path}")

print("PASS: SDK Python and private library resolution")
PY

echo "=== Verify CLI executables ==="

for command in \
    frida \
    frida-ps \
    frida-ls-devices \
    frida-trace \
    frida-kill \
    frida-ls \
    frida-discover \
    frida-compile
do
    binary=$(command -v "$command")
    case "$binary" in
        "$OECORE_NATIVE_SYSROOT"/*) ;;
        *)
            echo "ERROR: $command is outside SDK: $binary" >&2
            exit 1
            ;;
    esac

    echo "$command: $binary"
    "$command" --help >/dev/null
done

echo "=== Frida CLI version ==="
frida-ps --version

echo "=== Verify ELF relocation ==="

core=$(find "$OECORE_NATIVE_SYSROOT" \
    -name "libfrida-core-1.0.so" -type f -print -quit)

extension=$(find "$OECORE_NATIVE_SYSROOT" \
    -name "_frida*.so" -type f -print -quit)

test -n "$core"
test -n "$extension"

for binary in "$core" "$extension"; do
    echo "--- $binary ---"

    dynamic=$(readelf -d "$binary")
    printf '%s\n' "$dynamic" |
        grep -E "NEEDED|RPATH|RUNPATH" || true

    if printf '%s\n' "$dynamic" |
        grep -E "/work/build|oe-sdk-hardcoded-buildpath"; then
        echo "ERROR: unrelocated ELF path" >&2
        exit 1
    fi
done

echo "=== Verify Frida RUNPATH ==="

core_runpath=$(
    readelf -d "$core" |
        sed -n 's/.*(RUNPATH).*Library runpath: \[\([^]]*\)\].*/\1/p'
)

extension_runpath=$(
    readelf -d "$extension" |
        sed -n 's/.*(RUNPATH).*Library runpath: \[\([^]]*\)\].*/\1/p'
)

if [ "$core_runpath" != '$ORIGIN/frida/lib' ]; then
    echo "ERROR: unexpected Frida Core RUNPATH: $core_runpath" >&2
    exit 1
fi

if [ "$extension_runpath" != '$ORIGIN/../../../frida/lib:$ORIGIN/../../..' ]; then
    echo "ERROR: unexpected Frida Python RUNPATH: $extension_runpath" >&2
    exit 1
fi

echo "PASS: Frida private libraries precede standard SDK libraries"

echo "PASS: Installed SDK smoke test"

