# SPDX-License-Identifier: MIT

SUMMARY = "Frida's private Brotli libraries"
DESCRIPTION = "Frida-pinned Brotli encoder, decoder, and common libraries."
HOMEPAGE = "https://github.com/frida/brotli"

LICENSE = "MIT"
LIC_FILES_CHKSUM = "file://LICENSE;md5=941ee9cd1609382f946352712a319b4b"

PV = "1.0.9+git"

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
    for lib in brotlicommon brotlidec brotlienc; do
        test -f "${D}${FRIDA_DEPS_PREFIX}/lib/lib${lib}.a" || \
            bbfatal "Missing private Brotli library: lib${lib}.a"

        test -f "${D}${FRIDA_DEPS_PREFIX}/lib/pkgconfig/lib${lib}.pc" || \
            bbfatal "Missing private Brotli pkg-config metadata: lib${lib}.pc"
    done
}
