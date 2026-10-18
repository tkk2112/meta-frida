# SPDX-License-Identifier: MIT

SUMMARY = "Frida Gum instrumentation library"
DESCRIPTION = "Frida Gum C API, built for ARM64 without GumJS or Gum++."
HOMEPAGE = "https://github.com/frida/frida-gum"
LICENSE = "wxWindows"
NO_GENERIC_LICENSE[wxWindows] = "COPYING"
LIC_FILES_CHKSUM = "file://COPYING;beginline=1;endline=1;md5=10cdeddc933586f3c0c46d7869538e24"

DEPENDS = "\
    frida-capstone \
    frida-glib \
    frida-json-glib \
    frida-libdwarf \
    frida-libffi \
    frida-libunwind \
    frida-tinycc \
    glib-2.0-native \
    gobject-introspection \
    python3-native \
"

# GIR generation is not used for the cross-built SDK-host Gum libraries.
DEPENDS:remove:class-nativesdk = "gobject-introspection"

PV = "${FRIDA_VERSION}+git"

SRC_URI:append = " file://frida-gum.cross.in"

PACKAGECONFIG ??= ""
PACKAGECONFIG:append:class-nativesdk = " gumjs inspector"

PACKAGECONFIG[gumjs] = "-Dgumjs=enabled -Dquickjs=enabled, -Dgumjs=disabled -Dquickjs=disabled, frida-quickjs frida-quickjs-native"
PACKAGECONFIG[inspector] = "-Dinspector=enabled, -Dinspector=disabled, frida-libsoup"

inherit frida_meson python3native

MESON_CROSS_FILE:append:class-target = " --cross-file ${B}/frida-gum.cross"
MESON_CROSS_FILE:append:class-nativesdk = " --cross-file ${B}/frida-gum.cross"

PKG_CONFIG_PATH:prepend = "${STAGING_LIBDIR}/frida/lib/pkgconfig:"

# GumJS builds a native quickcompile helper using native QuickJS.
export EXTRA_NATIVE_PKGCONFIG_PATH = ":${STAGING_LIBDIR_NATIVE}/frida/lib/pkgconfig"

EXTRA_OEMESON:append = "\
    -Dfrida_version=${FRIDA_VERSION} \
    -Dgumpp=disabled \
    -Dgraft_tool=disabled \
    -Dtests=disabled \
"

FILES:${PN}-dev += "\
    ${FRIDA_DEPS_PREFIX}/include \
    ${FRIDA_DEPS_PREFIX}/lib/pkgconfig \
    ${FRIDA_DEPS_PREFIX}/share \
"

FILES:${PN}-staticdev += "\
    ${FRIDA_DEPS_PREFIX}/lib/*.a \
"

do_configure:prepend() {
    sed \
        -e "s|@FRIDA_SUBSYSTEM@|${FRIDA_MESON_SUBSYSTEM}|g" \
        "${UNPACKDIR}/frida-gum.cross.in" > "${B}/frida-gum.cross"
}

do_install:append() {
    test -f "${D}${FRIDA_DEPS_PREFIX}/lib/libfrida-gum-1.0.a" || \
        bbfatal "Missing static Frida Gum library"
    test -f "${D}${FRIDA_DEPS_PREFIX}/lib/pkgconfig/frida-gum-1.0.pc" || \
        bbfatal "Missing Frida Gum pkg-config metadata"
    test -f "${D}${FRIDA_DEPS_PREFIX}/include/frida-1.0/gum/gum.h" || \
        bbfatal "Missing Frida Gum C API headers"

    if ${@bb.utils.contains('PACKAGECONFIG', 'gumjs', 'true', 'false', d)}; then
        test -f "${D}${libdir}/frida/lib/libfrida-gumjs-1.0.a" || \
            bbfatal "Missing static Frida GumJS library"

        test -f "${D}${libdir}/frida/lib/pkgconfig/frida-gumjs-1.0.pc" || \
            bbfatal "Missing Frida GumJS pkg-config metadata"
    fi
}
