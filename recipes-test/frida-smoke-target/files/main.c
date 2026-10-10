#define _DEFAULT_SOURCE

#include <stdio.h>
#include <unistd.h>

__attribute__((noinline, visibility("default")))
int frida_smoke_add(int a, int b)
{
    return a + b;
}

int main(void)
{
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
