# SPDX-License-Identifier: MIT

SUMMARY = "Frida Vala compiler smoke test"
DESCRIPTION = "Builds and executes a Vala program using Frida's private Vala compiler."

LICENSE = "MIT"
LIC_FILES_CHKSUM = "file://${COMMON_LICENSE_DIR}/MIT;md5=0835ade698e0bcf8506ecda2f7b4f302"

DEPENDS = "\
    frida-vala-native \
    glib-2.0-native \
"

SRC_URI = "\
    file://meson.build \
    file://main.vala \
"

S = "${UNPACKDIR}"

inherit meson pkgconfig
inherit_defer native

MESONOPTS:append = " --native-file ${WORKDIR}/frida-vala.native"

do_write_config:append() {
    printf '%s\n' \
        '[binaries]' \
        "vala = '${STAGING_LIBDIR_NATIVE}/frida-vala/bin/valac'" \
        '' \
        '[built-in options]' \
        "vala_args = ['--vapidir=${STAGING_LIBDIR_NATIVE}/frida-vala/share/vala-0.58/vapi']" \
        > "${WORKDIR}/frida-vala.native"
}

do_smoketest() {
    output="$("${B}/frida-vala-smoketest")" || \
        bbfatal "Frida Vala smoke test executable failed"

    if [ "$output" != "frida vala smoke test" ]; then
        bbfatal "Unexpected Vala smoke test output: $output"
    fi

    bbplain "PASS: $output"
}

do_smoketest[nostamp] = "1"

addtask smoketest after do_compile

do_install() {
    :
}

