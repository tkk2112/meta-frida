/* SPDX-License-Identifier: MIT */
#include <gum/gum.h>

#include <stdio.h>

#if defined(__GNUC__)
#define NOINLINE __attribute__((noinline, noclone))
#else
#define NOINLINE
#endif

static NOINLINE int target_function(int value) {
  volatile int result = value + 1;
  return result;
}

static NOINLINE int replacement_function(int value) {
  volatile int result = value + 100;
  return result;
}

static int (* volatile call_target)(int) = target_function;

int main(void) {
  GumInterceptor* interceptor;
  GumReplaceReturn replace_result;
  int observed;
  int result = 1;

  gum_init_embedded();
  interceptor = gum_interceptor_obtain();

  observed = call_target(7);
  if (observed != 8) {
      fprintf(stderr, "before replacement: expected 8, got %d\n", observed);
      goto cleanup;
  }

  replace_result = gum_interceptor_replace(
      interceptor,
      (gpointer)target_function,
      (gpointer)replacement_function,
      NULL,
      NULL);
  if (replace_result != GUM_REPLACE_OK) {
      fprintf(stderr, "gum_interceptor_replace failed: %d\n", replace_result);
      goto cleanup;
  }

  observed = call_target(7);
  if (observed != 107) {
      fprintf(stderr, "after replacement: expected 107, got %d\n", observed);
      gum_interceptor_revert(interceptor, (gpointer) target_function);
      goto cleanup;
  }

  gum_interceptor_revert(interceptor, (gpointer) target_function);

  observed = call_target(7);
  if (observed != 8) {
      fprintf(stderr, "after revert: expected 8, got %d\n", observed);
      goto cleanup;
  }

  puts("PASS: Gum initialized, replaced and restored target function");
  result = 0;

cleanup:
  g_object_unref(interceptor);
  gum_deinit_embedded();
  return result;
}
