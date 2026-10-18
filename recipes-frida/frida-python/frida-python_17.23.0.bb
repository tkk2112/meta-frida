# SPDX-License-Identifier: MIT

SUMMARY = "Frida Python bindings"
DESCRIPTION = "Python bindings for the Frida instrumentation framework"
HOMEPAGE = "https://frida.re/"

LICENSE = "wxWindows"
LIC_FILES_CHKSUM = "file://COPYING;beginline=1;endline=7;md5=1d5e6a1f76dff6205d5a997bce134d2c"
NO_GENERIC_LICENSE[wxWindows] = "COPYING"

DEPENDS = "\
    frida-core \
    python3-setuptools-native \
"

SRC_URI = "https://files.pythonhosted.org/packages/source/f/frida/frida-${PV}.tar.gz"
SRC_URI[sha256sum] = "721284b8681eb745ac1e8ba20d99401121d8fcfce225efee5103f513d2752f13"
SRC_URI:append = " file://0001-meson-resolve-GIR-paths-through-cross-sysroot.patch"

S = "${UNPACKDIR}/frida-${PV}"

inherit meson python3targetconfig frida_sdk

# The GIR files and shared library must come from our packaged Frida Core.
EXTRA_OEMESON:append = " --wrap-mode=nodownload"

FILES:${PN} += "\
    ${PYTHON_SITEPACKAGES_DIR}/frida \
"

RDEPENDS:${PN}:append:class-nativesdk = " nativesdk-python3-core"

BBCLASSEXTEND = "nativesdk"
