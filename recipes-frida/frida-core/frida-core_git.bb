# SPDX-License-Identifier: MIT

SUMMARY = "Frida Core instrumentation framework"
DESCRIPTION = "Frida Core with the Linux local backend and frida-server."
HOMEPAGE = "https://frida.re/"

LICENSE = "wxWindows"
LIC_FILES_CHKSUM = "file://COPYING;beginline=1;endline=7;md5=1d5e6a1f76dff6205d5a997bce134d2c"
NO_GENERIC_LICENSE[wxWindows] = "COPYING"

DEPENDS = "\
    binutils-native \
    frida-brotli \
    frida-brotli-native \
    frida-capstone \
    frida-glib \
    frida-gum \
    frida-json-glib \
    frida-libbpf \
    frida-libgee \
    frida-libgee-native \
    frida-libsoup \
    frida-vala-native \
    glib-2.0-native \
    python3-native \
"

PV = "${FRIDA_VERSION}+git"

FRIDA_COMPONENT = "frida-core"

inherit frida_source meson pkgconfig

SRC_URI += "\
    file://frida-core.cross.in \
    file://frida-core.native.in \
    file://frida-valac.in \
"

FRIDA_VALAC = "${STAGING_LIBDIR_NATIVE}/frida-vala/bin/valac"
FRIDA_VAPIDIR = "${STAGING_LIBDIR_NATIVE}/frida-vala/share/vala-0.58/vapi"
FRIDA_TARGET_VAPIDIR = "${STAGING_LIBDIR}/frida/share/vala/vapi"

PKG_CONFIG_PATH:prepend = "${STAGING_LIBDIR}/frida/lib/pkgconfig:"
export EXTRA_NATIVE_PKGCONFIG_PATH = ":${STAGING_LIBDIR_NATIVE}/frida/lib/pkgconfig"

EXTRA_OEMESON:append = "\
    --cross-file=${B}/frida-core.cross \
    --native-file=${B}/frida-core.native \
    -Dfrida_version=${FRIDA_VERSION} \
    -Dlocal_backend=enabled \
    -Dsocket_backend=enabled \
    -Dsimmy_backend=disabled \
    -Dfruity_backend=disabled \
    -Ddroidy_backend=disabled \
    -Dbarebone_backend=disabled \
    -Dcompiler_backend=disabled \
    -Dserver=enabled \
    -Dportal=disabled \
    -Dinject=disabled \
    -Dgadget=disabled \
    -Dtests=disabled \
    -Dconnectivity=disabled \
    -Dmapper=disabled \
    -Dcompat=disabled \
    -Dassets=embedded \
    -Ddefault_library=static \
"

do_configure:prepend() {
    test -x "${FRIDA_VALAC}" || \
        bbfatal "Frida Vala compiler not found"

    test -f "${FRIDA_VAPIDIR}/glib-2.0.vapi" || \
        bbfatal "Frida Vala GLib VAPI not found"

    test -f "${FRIDA_VAPIDIR}/gobject-2.0.vapi" || \
        bbfatal "Frida Vala GObject VAPI not found"

    "${FRIDA_VALAC}" --version | grep -q -- '-frida' || \
        bbfatal "Frida-patched Vala compiler is required"

    install -m 0755 \
        "${UNPACKDIR}/frida-valac.in" \
        "${B}/frida-valac"

    sed -i \
        -e "s|@VALAC@|${FRIDA_VALAC}|g" \
        -e "s|@VAPIDIR@|${FRIDA_VAPIDIR}|g" \
        "${B}/frida-valac"

    for machine in cross native; do
        install -m 0644 \
            "${UNPACKDIR}/frida-core.${machine}.in" \
            "${B}/frida-core.${machine}"

        sed -i \
            -e "s|@FRIDA_VALAC@|${B}/frida-valac|g" \
            -e "s|@FRIDA_TARGET_VAPIDIR@|${FRIDA_TARGET_VAPIDIR}|g" \
            "${B}/frida-core.${machine}"
    done

    for package in frida-gum-1.0 gee-0.8; do
        test -f "${FRIDA_TARGET_VAPIDIR}/${package}.vapi" || \
            bbfatal "Target VAPI not found: ${package}"
    done
}

PACKAGES =+ "frida-server"

FILES:frida-server += "\
    ${bindir}/frida-server \
"

do_install:append() {
    test -f "${D}${bindir}/frida-server" || \
        bbfatal "frida-server was not installed"
}

FILES:${PN} += "\
    ${libdir}/girepository-1.0/Frida-1.0.typelib \
"

FILES:${PN}-dev += "\
    ${datadir}/gir-1.0 \
    ${datadir}/vala/vapi \
"
