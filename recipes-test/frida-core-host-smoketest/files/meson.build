project('frida-core-host-smoketest', 'c', version: '1.0')

frida = dependency('frida-core-1.0', static: false, required: true)

executable(
  'frida-core-host-smoketest',
  'main.c',
  dependencies: frida,
  install: true,
)
