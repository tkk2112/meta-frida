# SPDX-License-Identifier: MIT

SUMMARY = "Frida's private JSON-GLib"
DESCRIPTION = "Frida-pinned JSON-GLib built as a private static dependency."
HOMEPAGE = "https://github.com/frida/json-glib"

LICENSE = "LGPL-2.1-or-later"
LIC_FILES_CHKSUM = "file://COPYING;md5=41890f71f740302b785c27661123bff5"

PV = "1.8.0+git"

DEPENDS = "frida-glib"

inherit frida-dep-meson

PKG_CONFIG_PATH:prepend = "${STAGING_LIBDIR}/frida/lib/pkgconfig:"

FILES:${PN} += "\
    ${FRIDA_DEPS_PREFIX}/bin \
"

FILES:${PN}-dev += "\
    ${FRIDA_DEPS_PREFIX}/include \
    ${FRIDA_DEPS_PREFIX}/lib/pkgconfig \
"

FILES:${PN}-staticdev += "\
    ${FRIDA_DEPS_PREFIX}/lib/*.a \
"

do_configure:prepend() {
    for dependency in glib-2.0 gobject-2.0 gio-2.0; do
        resolved="$(
            PKG_CONFIG_PATH="${STAGING_LIBDIR}/frida/lib/pkgconfig" \
            pkg-config --variable=prefix "$dependency"
        )"

        test "$resolved" = "/usr/lib/frida" || \
            bbfatal "$dependency resolved to unexpected prefix: $resolved"
    done
}

do_install:append() {
    test -f "${D}${FRIDA_DEPS_PREFIX}/lib/libjson-glib-1.0.a" || \
        bbfatal "Private static JSON-GLib was not installed"

    test -f "${D}${FRIDA_DEPS_PREFIX}/include/json-glib-1.0/json-glib/json-glib.h" || \
        bbfatal "Private JSON-GLib headers were not installed"

    test -f "${D}${FRIDA_DEPS_PREFIX}/lib/pkgconfig/json-glib-1.0.pc" || \
        bbfatal "Private JSON-GLib pkg-config metadata was not installed"

    if find "${D}${libdir}" -maxdepth 1 \
        \( -name 'libjson-glib-1.0.so' -o \
           -name 'libjson-glib-1.0.so.*' -o \
           -name 'libjson-glib-1.0.a' \) \
        -print -quit | grep -q .; then
        bbfatal "frida-json-glib installed a public library"
    fi
}
