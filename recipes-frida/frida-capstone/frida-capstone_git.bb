SUMMARY = "Frida's Capstone fork"
DESCRIPTION = "Private static Capstone build for Frida"
HOMEPAGE = "https://github.com/frida/capstone"

LICENSE = "BSD-3-Clause"
LIC_FILES_CHKSUM = "file://LICENSE.TXT;md5=1cfbff4f40612b0144e498a47c91499c"

PV = "5.0.0+git"

inherit frida_dep_meson

EXTRA_OEMESON:append = " \
    -Dprofile=full \
"

FILES:${PN}-dev += "\
    ${FRIDA_DEPS_PREFIX}/include \
    ${FRIDA_DEPS_PREFIX}/lib/pkgconfig \
"

FILES:${PN}-staticdev += "\
    ${FRIDA_DEPS_PREFIX}/lib/*.a \
"
