# SPDX-License-Identifier: MIT

SUMMARY = "Frida's private PCRE2"
DESCRIPTION = "Frida-pinned PCRE2 built as a private static dependency."
HOMEPAGE = "https://github.com/frida/pcre2"

LICENSE = "BSD-3-Clause"
LIC_FILES_CHKSUM = "file://LICENCE.md;md5=6720bf3bcff57543b915c2b22e526df0"

PV = "10.41+git"

inherit frida_dep_meson

FILES:${PN}-dev += "\
    ${FRIDA_DEPS_PREFIX}/include \
    ${FRIDA_DEPS_PREFIX}/lib/pkgconfig \
"

FILES:${PN}-staticdev += "\
    ${FRIDA_DEPS_PREFIX}/lib/*.a \
"

do_install:append() {
    test -f "${D}${FRIDA_DEPS_PREFIX}/lib/libpcre2-8.a" || \
        bbfatal "Private static PCRE2 was not installed"

    test -f "${D}${FRIDA_DEPS_PREFIX}/include/pcre2.h" || \
        bbfatal "Private PCRE2 headers were not installed"

    test -f "${D}${FRIDA_DEPS_PREFIX}/lib/pkgconfig/libpcre2-8.pc" || \
        bbfatal "Private PCRE2 pkg-config metadata was not installed"

    if find "${D}${libdir}" -maxdepth 1 \
        \( -name 'libpcre2*.so' -o -name 'libpcre2*.so.*' -o -name 'libpcre2*.a' \) \
        -print -quit | grep -q .; then
        bbfatal "frida-pcre2 installed a public library"
    fi
}
