# SPDX-License-Identifier: MIT

SUMMARY = "Frida's private Public Suffix List library"
DESCRIPTION = "Frida-pinned libpsl built as a private static dependency."
HOMEPAGE = "https://github.com/frida/libpsl"

LICENSE = "MIT"
LIC_FILES_CHKSUM = "file://LICENSE;md5=49296c1806ef92c28297fb264163d81e"

PV = "1.0+git"

inherit frida_dep_meson

# nooelint: oelint.var.override - Fetch the pinned publicsuffix/list Git submodule.
SRC_URI = "${@d.getVar('FRIDA_SOURCE_URI').replace('git://', 'gitsm://', 1)}"

FILES:${PN} += "\
    ${FRIDA_DEPS_PREFIX}/bin \
    ${FRIDA_DEPS_PREFIX}/share/man \
"

FILES:${PN}-dev += "\
    ${FRIDA_DEPS_PREFIX}/include \
    ${FRIDA_DEPS_PREFIX}/lib/pkgconfig \
"

FILES:${PN}-staticdev += "\
    ${FRIDA_DEPS_PREFIX}/lib/*.a \
"

do_install:append() {
    test -f "${D}${FRIDA_DEPS_PREFIX}/lib/libpsl.a" || \
        bbfatal "Missing private libpsl static library"

    test -f "${D}${FRIDA_DEPS_PREFIX}/lib/pkgconfig/libpsl.pc" || \
        bbfatal "Missing private libpsl pkg-config metadata"

    test -f "${D}${FRIDA_DEPS_PREFIX}/include/libpsl.h" || \
        bbfatal "Missing private libpsl header"
}
