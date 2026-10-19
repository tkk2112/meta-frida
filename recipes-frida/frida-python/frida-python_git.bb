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
DEPENDS:append:class-nativesdk = " patchelf-native"

require conf/include/frida_lock.inc

PV = "${FRIDA_VERSION}"

SRC_URI = "https://files.pythonhosted.org/packages/source/f/frida/frida-${PV}.tar.gz"
SRC_URI[sha256sum] = "${FRIDA_PYTHON_SHA256}"
SRC_URI:append = " file://0001-meson-resolve-GIR-paths-through-cross-sysroot.patch"

S = "${UNPACKDIR}/frida-${PV}"

inherit meson python3targetconfig frida_sdk

do_install:append:class-nativesdk() {
    for extension in "${D}${PYTHON_SITEPACKAGES_DIR}/frida"/_frida*.so; do
        test -f "${extension}" || \
            bbfatal "Frida Python extension not installed"

        "${STAGING_BINDIR_NATIVE}/patchelf" \
            --set-rpath '$ORIGIN/../../../frida/lib:$ORIGIN/../../..' \
            "${extension}"
    done
}

# The GIR files and shared library must come from our packaged Frida Core.
EXTRA_OEMESON:append = " --wrap-mode=nodownload"

FILES:${PN} += "\
    ${PYTHON_SITEPACKAGES_DIR}/frida \
"

RDEPENDS:${PN}:append:class-nativesdk = " nativesdk-python3-core"

BBCLASSEXTEND = "nativesdk"
