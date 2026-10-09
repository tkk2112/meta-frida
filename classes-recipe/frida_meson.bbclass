# SPDX-License-Identifier: MIT

inherit frida_source meson pkgconfig

FRIDA_DEPS_PREFIX ??= "${libdir}/frida"
EXTRA_OEMESON:append = " \
    --prefix=${FRIDA_DEPS_PREFIX} \
    --bindir=bin \
    --libdir=lib \
    --includedir=include \
    --datadir=share \
    -Ddefault_library=static \
"
