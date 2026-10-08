# SPDX-License-Identifier: MIT

SUMMARY = "Private native Vala compiler for building Frida"
DESCRIPTION = "Bootstraps Frida's Vala fork with OE-Core's vala-native without replacing the stock compiler."
HOMEPAGE = "https://github.com/frida/vala"

LICENSE = "LGPL-2.1-or-later"
LIC_FILES_CHKSUM = "file://compiler/valacompiler.vala;beginline=1;endline=22;md5=2f745017010224f101a5cbc5eaa55926"

DEPENDS = "\
    bison-native \
    flex-native \
    glib-2.0-native \
"

PV = "0.58.0+git"

inherit frida_dep_meson vala
inherit_defer native

FRIDA_DEPS_PREFIX = "${libdir}/frida-vala"

EXTRA_OEMESON:append = " \
    -Dgir=disabled \
"

do_install:append() {
    test -x "${D}${FRIDA_DEPS_PREFIX}/bin/valac" || \
        bbfatal "Frida Vala compiler was not installed"

    for package in glib-2.0 gobject-2.0 gio-2.0; do
        test -r "${D}${FRIDA_DEPS_PREFIX}/share/vala-0.58/vapi/$package.vapi" || \
            bbfatal "Missing Frida Vala VAPI: $package"
    done
}
