# SPDX-License-Identifier: MIT

SUMMARY = "WebSocket protocol implementation"
DESCRIPTION = "WebSockets 13.1, retained for Frida SDK tooling compatibility."
HOMEPAGE = "https://github.com/python-websockets/websockets"

LICENSE = "BSD-3-Clause"
LIC_FILES_CHKSUM = "file://LICENSE;md5=51924a6af4495b8cfaee1b1da869b6f4"

PYPI_PACKAGE = "websockets"

SRC_URI[sha256sum] = "a3b3366087c1bc0a2795111edcadddb8b3b59509d5db5d7ea3fdd69f954a8878"

inherit pypi python_setuptools_build_meta

DEFAULT_PREFERENCE = "-1"
DEFAULT_PREFERENCE:class-nativesdk = "1"

RDEPENDS:${PN}:class-nativesdk = "\
    nativesdk-python3-asyncio \
"

BBCLASSEXTEND = "nativesdk"
