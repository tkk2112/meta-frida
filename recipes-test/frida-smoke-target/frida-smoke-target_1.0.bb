SUMMARY = "Deterministic target for Frida runtime smoke testing"
LICENSE = "CLOSED"

SRC_URI = "\
    file://main.c \
    file://meson.build \
"

S = "${UNPACKDIR}"

inherit meson

PACKAGE_ARCH = "${MACHINE_ARCH}"
