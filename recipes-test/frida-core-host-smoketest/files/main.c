/* SPDX-License-Identifier: MIT */

#include <frida-core.h>
#include <stdio.h>

int main(void)
{
    GError *error = NULL;
    int result = 0;

    frida_init();

    FridaDeviceManager *manager = frida_device_manager_new();

    FridaDeviceList *devices =
        frida_device_manager_enumerate_devices_sync(
            manager, NULL, &error);

    if (devices == NULL) {
        fprintf(stderr, "Failed to enumerate devices: %s\n",
                error != NULL ? error->message : "unknown error");
        result = 1;
    } else {
        int count = frida_device_list_size(devices);
        printf("Frida found %d device(s)\n", count);

        if (count < 1)
            result = 1;

        frida_unref(devices);
    }

    g_clear_error(&error);

    frida_device_manager_close_sync(manager, NULL, &error);
    if (error != NULL) {
        fprintf(stderr, "Failed to close device manager: %s\n",
                error->message);
        g_clear_error(&error);
        result = 1;
    }

    frida_unref(manager);
    frida_shutdown();
    frida_deinit();

    if (result == 0)
        puts("PASS: Frida Core initialized and enumerated devices");

    return result;
}
