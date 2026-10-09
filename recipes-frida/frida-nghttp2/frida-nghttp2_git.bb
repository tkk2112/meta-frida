# SPDX-License-Identifier: MIT

SUMMARY = "Frida's private nghttp2 library"
DESCRIPTION = "Frida-pinned HTTP/2 C library built as a private static dependency."
HOMEPAGE = "https://github.com/frida/nghttp2"

LICENSE = "MIT"
LIC_FILES_CHKSUM = "file://COPYING;md5=764abdf30b2eadd37ce47dcbce0ea1ec"

PV = "1.0+git"

inherit frida_dep_meson

FILES:${PN}-dev += "\
    ${FRIDA_DEPS_PREFIX}/include \
    ${FRIDA_DEPS_PREFIX}/lib/pkgconfig \
"

FILES:${PN}-staticdev += "\
    ${FRIDA_DEPS_PREFIX}/lib/*.a \
"

do_install:append() {
    test -f "${D}${FRIDA_DEPS_PREFIX}/lib/libnghttp2.a" || \
        bbfatal "Missing private nghttp2 static library"

    test -f "${D}${FRIDA_DEPS_PREFIX}/lib/pkgconfig/libnghttp2.pc" || \
        bbfatal "Missing private nghttp2 pkg-config metadata"

    test -f "${D}${FRIDA_DEPS_PREFIX}/include/nghttp2/nghttp2.h" || \
        bbfatal "Missing private nghttp2 header"
}
