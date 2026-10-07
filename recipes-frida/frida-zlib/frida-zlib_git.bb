# SPDX-License-Identifier: MIT

SUMMARY = "Frida's private zlib"
DESCRIPTION = "Frida-pinned zlib built as a private static dependency."
HOMEPAGE = "https://github.com/frida/zlib"

LICENSE = "Zlib"
LIC_FILES_CHKSUM = "file://zlib.h;beginline=6;endline=23;md5=5377232268e952e9ef63bc555f7aa6c0"

PV = "1.3.1+git"

inherit frida-source meson pkgconfig

FRIDA_DEPS_PREFIX = "${libdir}/frida"

EXTRA_OEMESON = " \
    --prefix=${FRIDA_DEPS_PREFIX} \
    --bindir=bin \
    --libdir=lib \
    --includedir=include \
    --datadir=share \
    -Ddefault_library=static \
"

FILES:${PN}-dev += "\
    ${FRIDA_DEPS_PREFIX}/include \
    ${FRIDA_DEPS_PREFIX}/lib/pkgconfig \
"

FILES:${PN}-staticdev += "\
    ${FRIDA_DEPS_PREFIX}/lib/*.a \
"

do_install:append() {
    test -f "${D}${FRIDA_DEPS_PREFIX}/lib/libz.a" || \
        bbfatal "Private static zlib was not installed"

    test -f "${D}${FRIDA_DEPS_PREFIX}/include/zlib.h" || \
        bbfatal "Private zlib headers were not installed"

    test -f "${D}${FRIDA_DEPS_PREFIX}/lib/pkgconfig/zlib.pc" || \
        bbfatal "Private zlib pkg-config metadata was not installed"

    if find "${D}${libdir}" -maxdepth 1 \
        \( -name 'libz.so' -o -name 'libz.so.*' -o -name 'libz.a' \) \
        -print -quit | grep -q .; then
        bbfatal "frida-zlib installed a public library"
    fi
}
