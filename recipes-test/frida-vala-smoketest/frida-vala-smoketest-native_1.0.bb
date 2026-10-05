# SPDX-License-Identifier: MIT

SUMMARY = "Frida Vala compiler smoke test"

LICENSE = "MIT"
LIC_FILES_CHKSUM = "file://${COMMON_LICENSE_DIR}/MIT;md5=0835ade698e0bcf8506ecda2f7b4f302"

SRC_URI = " \
    file://meson.build \
    file://main.vala \
"

S = "${UNPACKDIR}"

DEPENDS = " \
    frida-vala-native \
    glib-2.0-native \
"

inherit meson pkgconfig native

MESONOPTS:append = " --native-file ${WORKDIR}/frida-vala.native"

do_write_config:append() {
    cat > "${WORKDIR}/frida-vala.native" <<EOF
[binaries]
vala = '${STAGING_LIBDIR_NATIVE}/frida-vala/bin/valac'

[built-in options]
vala_args = ['--vapidir=${STAGING_LIBDIR_NATIVE}/frida-vala/share/vala-0.58/vapi']
EOF
}

do_compile:append() {
    "${B}/frida-vala-smoketest" | grep -F "frida vala smoke test"
}

do_install() {
    :
}
