# SPDX-License-Identifier: MIT

SUMMARY = "Frida's private libbpf"
DESCRIPTION = "Frida-pinned libbpf built as a private static dependency."
HOMEPAGE = "https://github.com/frida/libbpf"

LICENSE = "LGPL-2.1-only | BSD-2-Clause"
LIC_FILES_CHKSUM = "file://LICENSE;md5=ef85bb9c22630a7bfbcbbea6ec81ac72"

DEPENDS = "\
    elfutils \
    frida-zlib \
"

PV = "1.7.0+git"

inherit frida_dep_meson

PKG_CONFIG_PATH:prepend = "${STAGING_LIBDIR}/frida/lib/pkgconfig:"

FILES:${PN}-dev += "\
    ${FRIDA_DEPS_PREFIX}/include \
    ${FRIDA_DEPS_PREFIX}/lib/pkgconfig \
"

FILES:${PN}-staticdev += "\
    ${FRIDA_DEPS_PREFIX}/lib/*.a \
"

do_install:append() {
    test -f "${D}${FRIDA_DEPS_PREFIX}/lib/libbpf.a" || \
        bbfatal "Missing private static libbpf"

    test -f "${D}${FRIDA_DEPS_PREFIX}/lib/pkgconfig/libbpf.pc" || \
        bbfatal "Missing private libbpf pkg-config metadata"

    test -f "${D}${FRIDA_DEPS_PREFIX}/include/bpf/libbpf.h" || \
        bbfatal "Missing private libbpf headers"
}
