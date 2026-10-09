# SPDX-License-Identifier: MIT

SUMMARY = "Frida's private TinyCC library"
DESCRIPTION = "Frida-pinned libtcc for Gum CModule support."
HOMEPAGE = "https://github.com/frida/tinycc"
LICENSE = "LGPL-2.1-or-later"
LIC_FILES_CHKSUM = "file://COPYING;beginline=1;endline=1;md5=ed272f7c46b694d5112ee82b0f6c2b86"

PV = "0.9.27+git"

inherit frida_dep_meson

FILES:${PN}-dev += "\
    ${FRIDA_DEPS_PREFIX}/include \
    ${FRIDA_DEPS_PREFIX}/lib/pkgconfig \
    ${FRIDA_DEPS_PREFIX}/lib/tcc \
"

FILES:${PN}-staticdev += "\
    ${FRIDA_DEPS_PREFIX}/lib/*.a \
"

do_install:append() {
    test -f "${D}${FRIDA_DEPS_PREFIX}/lib/libtcc.a" || \
        bbfatal "Missing private TinyCC static library"
    test -f "${D}${FRIDA_DEPS_PREFIX}/lib/pkgconfig/libtcc.pc" || \
        bbfatal "Missing private TinyCC pkg-config metadata"
}
