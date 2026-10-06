# SPDX-License-Identifier: MIT

SUMMARY = "Frida's private libffi"
DESCRIPTION = "Frida-patched libffi built as a private static dependency."
HOMEPAGE = "https://github.com/frida/libffi"

LICENSE = "MIT"
LIC_FILES_CHKSUM = "file://LICENSE;md5=32c0d09a0641daf4903e5d61cc8f23a8"

SRC_URI = "git://github.com/frida/libffi.git;protocol=https;branch=main"
SRCREV = "3fe3257235cc9ffd192e1cd567f1bdfff751fa3e"

inherit meson pkgconfig

FRIDA_DEPS_PREFIX = "${libdir}/frida"

EXTRA_OEMESON = " \
    --prefix=${FRIDA_DEPS_PREFIX} \
    --bindir=bin \
    --libdir=lib \
    --includedir=include \
    --datadir=share \
    -Ddefault_library=static \
    -Dexe_static_tramp=false \
    -Dtests=false \
"

FILES:${PN}-dev += "\
    ${FRIDA_DEPS_PREFIX}/include \
    ${FRIDA_DEPS_PREFIX}/lib/pkgconfig \
"

FILES:${PN}-staticdev += "\
    ${FRIDA_DEPS_PREFIX}/lib/*.a \
"

do_install:append() {
    test -f "${D}${FRIDA_DEPS_PREFIX}/lib/libffi.a" || \
        bbfatal "Private static libffi was not installed"

    test -f "${D}${FRIDA_DEPS_PREFIX}/include/ffi.h" || \
        bbfatal "Private libffi headers were not installed"

    if find "${D}${libdir}" -maxdepth 1 \
        \( -name 'libffi.so' -o -name 'libffi.so.*' \) \
        -print -quit | grep -q .; then
        bbfatal "frida-libffi installed a public shared library"
    fi
}
