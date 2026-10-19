# SPDX-License-Identifier: MIT

SUMMARY = "Frida Linux SDK host tools"
DESCRIPTION = "Frida C API, Python bindings, and command-line tools for SDK-host Linux."
HOMEPAGE = "https://frida.re/"

LICENSE = "MIT"

SRC_URI = ""

inherit_defer nativesdk

ALLOW_EMPTY:${PN} = "1"

RDEPENDS:${PN} = "\
    nativesdk-frida-core \
    nativesdk-frida-python \
    nativesdk-frida-tools \
"
