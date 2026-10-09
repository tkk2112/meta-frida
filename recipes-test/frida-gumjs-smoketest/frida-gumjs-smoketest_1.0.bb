# SPDX-License-Identifier: MIT

SUMMARY = "Frida GumJS QuickJS smoke test"
DESCRIPTION = "Checks QuickJS script execution through Frida GumJS."
LICENSE = "MIT"
LIC_FILES_CHKSUM = "file://${COMMON_LICENSE_DIR}/MIT;md5=0835ade698e0bcf8506ecda2f7b4f302"

DEPENDS = "frida-gum"

SRC_URI = " \
    file://meson.build \
    file://main.c \
"

S = "${UNPACKDIR}"

inherit meson pkgconfig

PKG_CONFIG_PATH:prepend = "${STAGING_LIBDIR}/frida/lib/pkgconfig:"

do_install:append() {
    test -x "${D}${bindir}/frida-gumjs-smoketest" || \
        bbfatal "Missing Frida GumJS smoke test executable"
}
