# SPDX-License-Identifier: MIT

inherit frida_source meson pkgconfig frida_variants

FRIDA_DEPS_PREFIX ??= "${libdir}/frida"

FRIDA_MESON_PREFIX ??= "${FRIDA_DEPS_PREFIX}"
FRIDA_MESON_BINDIR ??= "bin"
FRIDA_MESON_LIBDIR ??= "lib"
FRIDA_MESON_INCLUDEDIR ??= "include"
FRIDA_MESON_DATADIR ??= "share"
FRIDA_MESON_LIBRARY ??= "static"

EXTRA_OEMESON:append = " \
    --prefix=${FRIDA_MESON_PREFIX} \
    --bindir=${FRIDA_MESON_BINDIR} \
    --libdir=${FRIDA_MESON_LIBDIR} \
    --includedir=${FRIDA_MESON_INCLUDEDIR} \
    --datadir=${FRIDA_MESON_DATADIR} \
    -Ddefault_library=${FRIDA_MESON_LIBRARY} \
"
