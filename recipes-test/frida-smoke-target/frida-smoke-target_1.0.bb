# SPDX-License-Identifier: MIT

SUMMARY = "Deterministic target for Frida runtime smoke testing"
DESCRIPTION = "Provides a controlled executable with known functions for Frida attachment and interception tests."

LICENSE = "CLOSED"

SRC_URI = "\
    file://main.c \
    file://meson.build \
"

S = "${UNPACKDIR}"

inherit meson

PACKAGE_ARCH = "${MACHINE_ARCH}"
