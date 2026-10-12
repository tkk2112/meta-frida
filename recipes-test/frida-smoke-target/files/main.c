#define _DEFAULT_SOURCE

#include <errno.h>
#include <fcntl.h>
#include <stdio.h>
#include <string.h>
#include <unistd.h>

__attribute__((noinline, visibility("default")))
int frida_smoke_add(int a, int b)
{
    return a + b;
}

static int test_io(void)
{
    for (;;) {
        int fd = open("/etc/passwd", O_RDONLY);

        if (fd < 0) {
            if (errno == EACCES)
                return 42;

            return 1;
        }

        close(fd);
        usleep(100000);
    }
}

int main(int argc, char **argv)
{
    if (argc == 2 && strcmp(argv[1], "io") == 0)
        return test_io();

    puts("frida-smoke ready");
    fflush(stdout);

    for (;;) {
        volatile int a = 7;
        volatile int b = 11;
        volatile int result = frida_smoke_add(a, b);

        if (result != 18)
            return 1;

        usleep(100000);
    }
}
