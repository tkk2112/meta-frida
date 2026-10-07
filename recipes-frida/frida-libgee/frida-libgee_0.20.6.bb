# SPDX-License-Identifier: MIT

SUMMARY = "Frida's private libgee"
DESCRIPTION = "Frida-pinned libgee built as a private static dependency."
HOMEPAGE = "https://github.com/frida/libgee"

LICENSE = "LGPL-2.1-only"
LIC_FILES_CHKSUM = "file://COPYING;md5=fbc093901857fcd118f065f900982c24"

PV = "0.20.6+git"

DEPENDS = "\
    frida-glib \
    frida-vala-native \
"

inherit frida-source meson pkgconfig

FRIDA_DEPS_PREFIX = "${libdir}/frida"

PKG_CONFIG_PATH:prepend = "${STAGING_LIBDIR}/frida/lib/pkgconfig:"

EXTRA_OEMESON = " \
    --prefix=${FRIDA_DEPS_PREFIX} \
    --bindir=bin \
    --libdir=lib \
    --includedir=include \
    --datadir=share \
    -Ddefault_library=static \
    -Ddisable-internal-asserts=true \
    -Ddisable-introspection=true \
    --native-file=${WORKDIR}/frida-vala.ini \
"

do_configure:prepend() {
    cat > "${WORKDIR}/frida-valac" <<EOF
#!/bin/sh
exec "${STAGING_LIBDIR_NATIVE}/frida-vala/bin/valac" \
    --vapidir="${STAGING_LIBDIR_NATIVE}/frida-vala/share/vala-0.58/vapi" \
    "\$@"
EOF
    chmod 0755 "${WORKDIR}/frida-valac"

    cat > "${WORKDIR}/frida-vala.ini" <<EOF
[binaries]
vala = '${WORKDIR}/frida-valac'
EOF

    for dependency in glib-2.0 gobject-2.0 gio-2.0; do
        resolved="$(
            PKG_CONFIG_PATH="${STAGING_LIBDIR}/frida/lib/pkgconfig" \
            pkg-config --variable=prefix "$dependency"
        )"

        test "$resolved" = "/usr/lib/frida" || \
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
