# SPDX-License-Identifier: MIT

SUMMARY = "Frida Gum instrumentation library"
DESCRIPTION = "Frida Gum C API, built for ARM64 without GumJS or Gum++."
HOMEPAGE = "https://github.com/frida/frida-gum"
LICENSE = "wxWindows"
NO_GENERIC_LICENSE[wxWindows] = "COPYING"
LIC_FILES_CHKSUM = "file://COPYING;beginline=1;endline=1;md5=10cdeddc933586f3c0c46d7869538e24"

DEPENDS = "\
    frida-capstone \
    frida-glib \
    frida-json-glib \
    frida-libdwarf \
    frida-libffi \
    frida-libunwind \
    frida-tinycc \
    glib-2.0-native \
    python3-native \
"

PV = "${FRIDA_VERSION}+git"

SRC_URI:append = " file://frida-linux.cross"
inherit frida_meson python3native

MESON_CROSS_FILE:append:class-target = " --cross-file ${UNPACKDIR}/frida-linux.cross"

PKG_CONFIG_PATH:prepend = "${STAGING_LIBDIR}/frida/lib/pkgconfig:"

EXTRA_OEMESON:append = "\
    -Dfrida_version=${FRIDA_VERSION} \
    -Dgumpp=disabled \
    -Dgumjs=disabled \
    -Dinspector=disabled \
    -Dgraft_tool=disabled \
    -Dtests=disabled \
"

FILES:${PN}-dev += "\
    ${FRIDA_DEPS_PREFIX}/include \
    ${FRIDA_DEPS_PREFIX}/lib/pkgconfig \
    ${FRIDA_DEPS_PREFIX}/share \
"

FILES:${PN}-staticdev += "\
    ${FRIDA_DEPS_PREFIX}/lib/*.a \
"

do_install:append() {
    test -f "${D}${FRIDA_DEPS_PREFIX}/lib/libfrida-gum-1.0.a" || \
        bbfatal "Missing static Frida Gum library"
    test -f "${D}${FRIDA_DEPS_PREFIX}/lib/pkgconfig/frida-gum-1.0.pc" || \
        bbfatal "Missing Frida Gum pkg-config metadata"
    test -f "${D}${FRIDA_DEPS_PREFIX}/include/frida-1.0/gum/gum.h" || \
        bbfatal "Missing Frida Gum C API headers"
}
