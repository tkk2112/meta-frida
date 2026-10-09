# SPDX-License-Identifier: MIT

SUMMARY = "Frida's private libsoup HTTP and WebSocket library"
DESCRIPTION = "Frida-pinned libsoup 3 built with private static dependencies."
HOMEPAGE = "https://github.com/frida/libsoup"

LICENSE = "LGPL-2.0-or-later"
LIC_FILES_CHKSUM = "file://COPYING;beginline=1;endline=7;md5=842402e2b7cecf311ceb3bf43fd49857"

DEPENDS = "\
    frida-brotli \
    frida-glib \
    frida-libpsl \
    frida-nghttp2 \
    frida-sqlite \
    frida-zlib \
    glib-2.0-native \
"

PV = "1.0+git"

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
    test -f "${D}${FRIDA_DEPS_PREFIX}/lib/libsoup-3.0.a" || \
        bbfatal "Missing private libsoup static library"

    test -f "${D}${FRIDA_DEPS_PREFIX}/lib/pkgconfig/libsoup-3.0.pc" || \
        bbfatal "Missing private libsoup pkg-config metadata"

    test -f "${D}${FRIDA_DEPS_PREFIX}/include/libsoup-3.0/libsoup/soup.h" || \
        bbfatal "Missing private libsoup headers"

    # Private static library; translated messages are not required.
    rm -rf "${D}${FRIDA_DEPS_PREFIX}/share/locale"
    rmdir "${D}${FRIDA_DEPS_PREFIX}/share" 2>/dev/null || true
}
