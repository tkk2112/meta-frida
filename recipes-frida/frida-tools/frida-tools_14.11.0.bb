# SPDX-License-Identifier: MIT

SUMMARY = "Frida command-line tools"
DESCRIPTION = "Interactive instrumentation, process discovery, tracing, and other Frida CLI utilities."
HOMEPAGE = "https://frida.re/"

LICENSE = "wxWindows"
NO_GENERIC_LICENSE[wxWindows] = "COPYING"
LIC_FILES_CHKSUM = "file://COPYING;beginline=1;endline=1;md5=10cdeddc933586f3c0c46d7869538e24"

PYPI_PACKAGE = "frida_tools"

SRC_URI[sha256sum] = "b8c772e59502be43b76df9feccadd5d342b5ca325066dd0c2384e63fa88da921"

inherit pypi python_setuptools_build_meta

FILES:${PN} += "\
    ${PYTHON_SITEPACKAGES_DIR}/frida_tools \
"

RDEPENDS:${PN}:class-nativesdk = "\
    nativesdk-frida-python (>= 17.10.0) \
    nativesdk-frida-python (< 18.0.0) \
    nativesdk-python3-colorama (>= 0.2.7) \
    nativesdk-python3-colorama (< 1.0.0) \
    nativesdk-python3-modules \
    nativesdk-python3-prompt-toolkit (>= 2.0.0) \
    nativesdk-python3-prompt-toolkit (< 4.0.0) \
    nativesdk-python3-pygments (>= 2.0.2) \
    nativesdk-python3-pygments (< 3.0.0) \
    nativesdk-python3-websockets (>= 13.0.0) \
    nativesdk-python3-websockets (< 14.0.0) \
"

do_install:append:class-nativesdk() {
    for command in \
        frida \
        frida-ls-devices \
        frida-ps \
        frida-kill \
        frida-ls \
        frida-rm \
        frida-pull \
        frida-push \
        frida-discover \
        frida-trace \
        frida-strace \
        frida-itrace \
        frida-join \
        frida-create \
        frida-compile \
        frida-pm \
        frida-apk
    do
        test -f "${D}${bindir}/${command}" || \
            bbfatal "Missing Frida command: ${command}"
    done

    for asset in \
        repl_agent.js \
        tracer_agent.js \
        tracer_ui.zip
    do
        test -s "${D}${PYTHON_SITEPACKAGES_DIR}/frida_tools/${asset}" || \
            bbfatal "Missing Frida asset: ${asset}"
    done
}

BBCLASSEXTEND = "nativesdk"
