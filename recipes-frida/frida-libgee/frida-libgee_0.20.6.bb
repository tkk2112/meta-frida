# SPDX-License-Identifier: MIT

SUMMARY = "Frida's private libgee"
DESCRIPTION = "Frida-pinned libgee built as a private static dependency."
HOMEPAGE = "https://github.com/frida/libgee"

LICENSE = "LGPL-2.1-only"
LIC_FILES_CHKSUM = "file://COPYING;md5=fbc093901857fcd118f065f900982c24"

DEPENDS = "\
    frida-glib \
    frida-vala-native \
"

PV = "0.20.6+git"

SRC_URI:append = " \
    file://frida-valac \
    file://frida-vala.ini \
"

inherit frida_dep_meson

PKG_CONFIG_PATH:prepend = "${STAGING_LIBDIR}/frida/lib/pkgconfig:"

EXTRA_OEMESON:append = "\
    --native-file=${B}/frida-vala.ini \
"
do_configure:prepend() {
    install -m 0755 "${WORKDIR}/frida-valac" "${B}/frida-valac"
    install -m 0644 "${WORKDIR}/frida-vala.ini" "${B}/frida-vala.ini"

    sed -i \
        -e "s|@VALAC@|${STAGING_LIBDIR_NATIVE}/frida-vala/bin/valac|g" \
        -e "s|@VAPIDIR@|${STAGING_LIBDIR_NATIVE}/frida-vala/share/vala-0.58/vapi|g" \
        "${B}/frida-valac"

    sed -i \
        -e "s|@FRIDA_VALAC@|${B}/frida-valac|g" \
        "${B}/frida-vala.ini"

    for dependency in glib-2.0 gobject-2.0 gio-2.0; do
        resolved="$(
            PKG_CONFIG_PATH="${STAGING_LIBDIR}/frida/lib/pkgconfig" \
            pkg-config --variable=prefix "$dependency"
        )"

        test "$resolved" = "${FRIDA_DEPS_PREFIX}" || \
            bbfatal "$dependency resolved to unexpected prefix: $resolved"
    done

    "${STAGING_LIBDIR_NATIVE}/frida-vala/bin/valac" --version | \
        grep -q -- '-frida' || \
        bbfatal "Frida Vala compiler is not being used"
}

FILES:${PN}-dev += "\
    ${FRIDA_DEPS_PREFIX}/include \
    ${FRIDA_DEPS_PREFIX}/lib/pkgconfig \
    ${FRIDA_DEPS_PREFIX}/share/vala \
"

FILES:${PN}-staticdev += "\
    ${FRIDA_DEPS_PREFIX}/lib/*.a \
"

do_install:append() {
    test -f "${D}${FRIDA_DEPS_PREFIX}/lib/libgee-0.8.a" || \
        bbfatal "Private static libgee was not installed"

    test -f "${D}${FRIDA_DEPS_PREFIX}/lib/pkgconfig/gee-0.8.pc" || \
        bbfatal "Private libgee pkg-config metadata was not installed"

    if find "${D}${libdir}" -maxdepth 1 \
        \( -name 'libgee-0.8.so' -o \
           -name 'libgee-0.8.so.*' -o \
           -name 'libgee-0.8.a' \) \
        -print -quit | grep -q .; then
        bbfatal "frida-libgee installed a public library"
    fi
}
