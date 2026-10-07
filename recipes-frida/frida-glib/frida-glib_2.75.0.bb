# SPDX-License-Identifier: MIT

SUMMARY = "Frida's private GLib"
DESCRIPTION = "Frida-patched GLib built as a private static dependency."
HOMEPAGE = "https://github.com/frida/glib"

LICENSE = "LGPL-2.1-or-later"
LIC_FILES_CHKSUM = "file://COPYING;md5=41890f71f740302b785c27661123bff5"

inherit frida-source meson pkgconfig

SRC_URI = " \
    ${FRIDA_SOURCE_URI};name=glib \
    ${FRIDA_GLIB_GVDB_URI};name=gvdb;destsuffix=${BP}/subprojects/gvdb \
"

SRCREV_glib = "${FRIDA_SOURCE_SRCREV}"
SRCREV_gvdb = "${FRIDA_GLIB_GVDB_SRCREV}"
SRCREV_FORMAT = "glib_gvdb"

PV = "2.75.0+git"

DEPENDS = " \
    frida-libffi \
    frida-pcre2 \
    frida-zlib \
"

inherit meson pkgconfig

FRIDA_DEPS_PREFIX = "${libdir}/frida"

PKG_CONFIG_PATH:prepend = "${STAGING_LIBDIR}/frida/lib/pkgconfig:"

EXTRA_OEMESON = " \
    --prefix=${FRIDA_DEPS_PREFIX} \
    --bindir=bin \
    --libdir=lib \
    --libexecdir=libexec \
    --includedir=include \
    --datadir=share \
    -Ddefault_library=static \
    -Dcocoa=disabled \
    -Dselinux=disabled \
    -Dxattr=false \
    -Dlibmount=disabled \
    -Dtests=false \
"

FILES:${PN}-dev += " \
    ${FRIDA_DEPS_PREFIX} \
"

FILES:${PN}-staticdev += " \
    ${FRIDA_DEPS_PREFIX}/lib/*.a \
"

do_configure:prepend() {
    for dependency in libffi libpcre2-8 zlib; do
        resolved="$(
            PKG_CONFIG_PATH="${STAGING_LIBDIR}/frida/lib/pkgconfig" \
            pkg-config --variable=prefix "$dependency"
        )"

        test "$resolved" = "/usr/lib/frida" || \
            bbfatal "$dependency resolved to unexpected prefix: $resolved"
    done
}

do_install:append() {
    for library in \
        libglib-2.0.a \
        libgobject-2.0.a \
        libgio-2.0.a \
        libgmodule-2.0.a \
        libgthread-2.0.a
    do
        test -f "${D}${FRIDA_DEPS_PREFIX}/lib/$library" || \
            bbfatal "Missing private GLib library: $library"
    done

    test -f "${D}${FRIDA_DEPS_PREFIX}/include/glib-2.0/glib.h" || \
        bbfatal "Private GLib headers were not installed"

    if find "${D}${libdir}" -maxdepth 1 \
        \( -name 'libglib-2.0*' -o \
           -name 'libgobject-2.0*' -o \
           -name 'libgio-2.0*' \) \
        -print -quit | grep -q .; then
        bbfatal "frida-glib installed a public library"
    fi
}
