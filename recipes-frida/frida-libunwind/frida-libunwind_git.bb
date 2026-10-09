# SPDX-License-Identifier: MIT

SUMMARY = "Frida's private libunwind"
DESCRIPTION = "Frida-pinned libunwind built as a private static dependency."
HOMEPAGE = "https://github.com/frida/libunwind"
LICENSE = "MIT"
LIC_FILES_CHKSUM = "file://COPYING;beginline=1;endline=1;md5=57f781dc64958d0a9397a3259c5e31de"

DEPENDS = "\
    frida-zlib \
    xz \
"

PV = "1.6+git"

inherit frida_dep_meson

PKG_CONFIG_PATH:prepend = "${STAGING_LIBDIR}/frida/lib/pkgconfig:"

# Frida builds libunwind as a Meson subproject, suppressing warnings.
# A standalone build exposes the AArch64 context-pointer mismatch.
CFLAGS:append:aarch64 = " -Wno-error=incompatible-pointer-types"

FILES:${PN}-dev += "\
    ${FRIDA_DEPS_PREFIX}/include \
    ${FRIDA_DEPS_PREFIX}/lib/pkgconfig \
"

FILES:${PN}-staticdev += "\
    ${FRIDA_DEPS_PREFIX}/lib/*.a \
"

do_install:append() {
    test -f "${D}${FRIDA_DEPS_PREFIX}/lib/libunwind.a" || \
        bbfatal "Missing private libunwind static library"
    test -f "${D}${FRIDA_DEPS_PREFIX}/lib/pkgconfig/libunwind.pc" || \
        bbfatal "Missing private libunwind pkg-config metadata"
}
