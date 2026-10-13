# SPDX-License-Identifier: MIT

inherit pkgconfig

# Expose Frida's private dependency metadata to SDK consumers.
PKG_CONFIG_PATH:prepend = "${STAGING_LIBDIR}/frida/lib/pkgconfig:"
