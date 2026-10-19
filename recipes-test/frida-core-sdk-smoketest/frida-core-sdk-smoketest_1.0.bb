# SPDX-License-Identifier: MIT

SUMMARY = "Frida Core SDK compile and link test"
DESCRIPTION = "Verifies that target SDK consumers can compile and link against the Frida Core C API."

LICENSE = "CLOSED"

DEPENDS = "\
    frida-core \
"

SRC_URI = "\
    file://main.c \
    file://meson.build \
"

S = "${UNPACKDIR}"

inherit meson frida_sdk
