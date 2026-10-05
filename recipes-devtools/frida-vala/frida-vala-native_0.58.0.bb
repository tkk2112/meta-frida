# SPDX-License-Identifier: MIT

SUMMARY = "Private native Vala compiler for building Frida"
DESCRIPTION = "Bootstraps Frida's Vala fork with OE-Core's vala-native without replacing the stock compiler."
HOMEPAGE = "https://github.com/frida/vala"

LICENSE = "LGPL-2.1-or-later"
LIC_FILES_CHKSUM = "file://compiler/valacompiler.vala;beginline=1;endline=22;md5=2f745017010224f101a5cbc5eaa55926"

SRC_URI = "git://github.com/frida/vala.git;protocol=https;branch=main"
SRCREV = "172348fa9123ff4a95d541c5f9e56837434c4b6e"

PV = "0.58.0+git"

inherit meson pkgconfig vala native

DEPENDS += "\
    glib-2.0-native \
    flex-native \
    bison-native \
"

FRIDA_VALA_PREFIX = "${libdir}/frida-vala"

EXTRA_OEMESON = " \
    --prefix=${FRIDA_VALA_PREFIX} \
    --bindir=bin \
    --sbindir=sbin \
    --libdir=lib \
    --libexecdir=libexec \
    --includedir=include \
    --datadir=share \
    --mandir=share/man \
    --infodir=share/info \
    --sysconfdir=etc \
    --localstatedir=var \
    --sharedstatedir=com \
    -Ddefault_library=static \
    -Dgir=disabled \
"

do_install:append() {
    test -x "${D}${FRIDA_VALA_PREFIX}/bin/valac" || \
        bbfatal "Frida Vala compiler was not installed"

    for package in glib-2.0 gobject-2.0 gio-2.0; do
        test -r "${D}${FRIDA_VALA_PREFIX}/share/vala-0.58/vapi/$package.vapi" || \
            bbfatal "Missing Frida Vala VAPI: $package"
    done
}
