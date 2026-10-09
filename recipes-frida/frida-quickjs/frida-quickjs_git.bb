# SPDX-License-Identifier: MIT

SUMMARY = "Frida's private QuickJS runtime"
DESCRIPTION = "Frida-pinned QuickJS built as a private static dependency."
HOMEPAGE = "https://github.com/frida/quickjs"

LICENSE = "MIT"
LIC_FILES_CHKSUM = "file://LICENSE;beginline=1;endline=1;md5=38d592ea8be958da616b924c00d838a1"

PV = "2024.01.13+git"

inherit frida_dep_meson

FILES:${PN}-dev += "\
    ${FRIDA_DEPS_PREFIX}/include \
    ${FRIDA_DEPS_PREFIX}/lib/pkgconfig \
"

FILES:${PN}-staticdev += "\
    ${FRIDA_DEPS_PREFIX}/lib/*.a \
"

BBCLASSEXTEND = "native"

do_install:append() {
    test -f "${D}${FRIDA_DEPS_PREFIX}/lib/libquickjs.a" || \
        bbfatal "Missing private QuickJS static library"

    test -f "${D}${FRIDA_DEPS_PREFIX}/lib/pkgconfig/quickjs.pc" || \
        bbfatal "Missing private QuickJS pkg-config metadata"

    test -f "${D}${FRIDA_DEPS_PREFIX}/include/quickjs/quickjs.h" || \
        bbfatal "Missing private QuickJS header"
}
