/* SPDX-License-Identifier: MIT */

#include <gum/gum.h>
#include <gumjs/gumscriptbackend.h>
#include <json-glib/json-glib.h>

#include <stdio.h>

typedef struct {
  GMainLoop* loop;
  gboolean received;
  gboolean valid;
} TestState;

static void on_message(const gchar* message, GBytes* data, gpointer user_data) {
  TestState* state = user_data;
  JsonParser* parser = json_parser_new();
  gboolean valid = FALSE;

  (void)data;

  if (json_parser_load_from_data(parser, message, -1, NULL)) {
    JsonNode* root = json_parser_get_root(parser);

    if (JSON_NODE_HOLDS_OBJECT(root)) {
      JsonObject* object = json_node_get_object(root);

      if (json_object_has_member(object, "type") &&
          json_object_has_member(object, "payload")) {
        valid = g_strcmp0(json_object_get_string_member(object, "type"), "send") == 0 &&
                json_object_get_int_member(object, "payload") == 42;
      }
    }
  }

  if (!valid) {
    fprintf(stderr, "Unexpected GumJS message: %s\n", message);
  }

  state->received = TRUE;
  state->valid = valid;
  g_main_loop_quit(state->loop);

  g_object_unref(parser);
}

static gboolean on_timeout(gpointer user_data) {
  TestState* state = user_data;
  g_main_loop_quit(state->loop);
  return G_SOURCE_REMOVE;
}

int main(void) {
  GumScriptBackend* backend;
  GumScript* script = NULL;
  GMainContext* context;
  GError* error = NULL;
  TestState state = {0};
  int result = 1;

  gum_init_embedded();

  context = g_main_context_ref_thread_default();
  state.loop = g_main_loop_new(context, FALSE);
  g_main_context_unref(context);

  backend = gum_script_backend_obtain_qjs();
  if (backend == NULL) {
    fprintf(stderr, "QuickJS backend unavailable\n");
    goto cleanup;
  }

  script = gum_script_backend_create_sync(
      backend, "smoketest", "send(42);", NULL, NULL, &error);

  if (script == NULL) {
    fprintf(stderr, "Script creation failed: %s\n",
            error != NULL ? error->message : "unknown error");
    goto cleanup;
  }

  gum_script_set_message_handler(script, on_message, &state, NULL);
  gum_script_load_sync(script, NULL);

  if (!state.received) {
    GSource* timeout = g_timeout_source_new_seconds(10);

    g_source_set_callback(timeout, on_timeout, &state, NULL);
    g_source_attach(timeout, g_main_loop_get_context(state.loop));

    g_main_loop_run(state.loop);

    g_source_destroy(timeout);
    g_source_unref(timeout);
  }

  if (!state.received) {
    fprintf(stderr, "Timed out waiting for GumJS message\n");
    goto cleanup;
  }

  if (!state.valid) {
    fprintf(stderr, "GumJS returned an unexpected message\n");
    goto cleanup;
  }

  puts("PASS: GumJS executed QuickJS script and delivered message");
  result = 0;

cleanup:
  if (script != NULL) {
    gum_script_unload_sync(script, NULL);
    g_object_unref(script);
  }

  g_clear_error(&error);
  g_main_loop_unref(state.loop);
  gum_deinit_embedded();

  return result;
}
