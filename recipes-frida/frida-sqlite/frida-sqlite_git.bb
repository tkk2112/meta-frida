# SPDX-License-Identifier: MIT

SUMMARY = "Frida's private SQLite library"
DESCRIPTION = "Frida-pinned SQLite amalgamation built as a private static dependency."
HOMEPAGE = "https://github.com/frida/sqlite"

LICENSE = "PD"
LIC_FILES_CHKSUM = "file://sqlite3.h;beginline=1;endline=10;md5=dc2c8c620a410b7ae4b7d83d3e2e7c15"

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
    test -f "${D}${FRIDA_DEPS_PREFIX}/lib/libsqlite3.a" || \
        bbfatal "Missing private SQLite static library"

    test -f "${D}${FRIDA_DEPS_PREFIX}/lib/pkgconfig/sqlite3.pc" || \
        bbfatal "Missing private SQLite pkg-config metadata"

    test -f "${D}${FRIDA_DEPS_PREFIX}/include/sqlite3.h" || \
        bbfatal "Missing private SQLite header"
}
