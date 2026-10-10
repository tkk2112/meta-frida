project(
  'frida-smoke-target',
  'c',
  version: '1.0',
  default_options: ['c_std=c11'],
)

executable(
  'frida-smoke',
  'main.c',
  link_args: ['-Wl,--export-dynamic'],
  install: true,
)
