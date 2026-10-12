project(
  'frida-core-sdk-smoketest',
  'c',
  version: '1.0',
  default_options: ['c_std=c11'],
)

frida_core = dependency('frida-core-1.0', static: true, required: true)

executable(
  'frida-core-sdk-smoketest',
  'main.c',
  dependencies: [frida_core],
  install: true,
)

