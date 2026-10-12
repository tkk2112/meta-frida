# Expose Frida's private static dependency metadata to SDK consumers.
# Ordinary recipes retain Yocto's standard pkg-config search paths.

PKG_CONFIG_PATH:prepend = "${RECIPE_SYSROOT}${libdir}/frida/lib/pkgconfig:"
