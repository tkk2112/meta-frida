# SPDX-License-Identifier: MIT

SUMMARY = "Frida's private libdwarf"
DESCRIPTION = "Frida-pinned libdwarf built as a private static dependency."
HOMEPAGE = "https://github.com/frida/libdwarf"
LICENSE = "LGPL-2.1-only & BSD-2-Clause"
LIC_FILES_CHKSUM = "file://COPYING;beginline=1;endline=1;md5=21a5726f87126c2003b0bf3c9c6106ba"

PV = "0.11.2+git"

inherit frida_dep_meson

FILES:${PN}-dev += "\
    ${FRIDA_DEPS_PREFIX}/include \
    ${FRIDA_DEPS_PREFIX}/lib/pkgconfig \
"

FILES:${PN}-staticdev += "\
    ${FRIDA_DEPS_PREFIX}/lib/*.a \
"

do_install:append() {
    rm -rf "${D}${FRIDA_DEPS_PREFIX}/bin" \
        "${D}${FRIDA_DEPS_PREFIX}/share/dwarfdump" \
        "${D}${FRIDA_DEPS_PREFIX}/share/man"

    if [ -d "${D}${FRIDA_DEPS_PREFIX}/share" ]; then
        rmdir "${D}${FRIDA_DEPS_PREFIX}/share"
    fi

    test -f "${D}${FRIDA_DEPS_PREFIX}/lib/libdwarf.a" || \
        bbfatal "Missing private libdwarf static library"
    test -f "${D}${FRIDA_DEPS_PREFIX}/lib/pkgconfig/libdwarf.pc" || \
        bbfatal "Missing private libdwarf pkg-config metadata"
}
