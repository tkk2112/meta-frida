SUMMARY = "Frida Core SDK compile and link test"
LICENSE = "CLOSED"

DEPENDS = "\
    frida-core \
"

SRC_URI = "\
    file://main.c \
    file://meson.build \
"

S = "${UNPACKDIR}"

inherit meson pkgconfig frida_sdk
