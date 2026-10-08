# SPDX-License-Identifier: MIT

require conf/include/frida-lock.inc

FRIDA_DEP ??= ""
FRIDA_COMPONENT ??= ""

def frida_source_identity(d):
    explicit_dep = d.getVar("FRIDA_DEP")
    explicit_component = d.getVar("FRIDA_COMPONENT")

    if explicit_dep and explicit_component:
        bb.fatal(
            "%s must not set both FRIDA_DEP and FRIDA_COMPONENT"
            % d.getVar("PN")
        )

    if explicit_component:
        return ("COMPONENT", explicit_component)

    if explicit_dep:
        return ("DEP", explicit_dep)

    bpn = d.getVar("BPN")

    if d.getVarFlag("FRIDA_COMPONENT_SRCREV", bpn):
        return ("COMPONENT", bpn)

    if not bpn.startswith("frida-"):
        bb.fatal(
            "%s: cannot derive Frida dependency from BPN %r"
            % (d.getVar("PN"), bpn)
        )

    dep = bpn.removeprefix("frida-")

    if not d.getVarFlag("FRIDA_DEP_SRCREV", dep):
        bb.fatal(
            "%s: neither FRIDA_COMPONENT_SRCREV[%s] nor "
            "FRIDA_DEP_SRCREV[%s] exists in frida-lock.inc"
            % (d.getVar("PN"), bpn, dep)
        )

    return ("DEP", dep)


def frida_source_value(d, field):
    kind, identifier = frida_source_identity(d)

    variable = "FRIDA_%s_%s" % (kind, field)
    value = d.getVarFlag(variable, identifier)

    if not value:
        bb.fatal(
            "%s: %s[%s] is missing from frida-lock.inc"
            % (d.getVar("PN"), variable, identifier)
        )

    return value

FRIDA_SOURCE_KIND = "${@frida_source_identity(d)[0]}"
FRIDA_SOURCE_NAME = "${@frida_source_identity(d)[1]}"
FRIDA_SOURCE_URI = "${@frida_source_value(d, 'URI')}"
FRIDA_SOURCE_SRCREV = "${@frida_source_value(d, 'SRCREV')}"

SRC_URI = "${FRIDA_SOURCE_URI}"
SRCREV = "${FRIDA_SOURCE_SRCREV}"
