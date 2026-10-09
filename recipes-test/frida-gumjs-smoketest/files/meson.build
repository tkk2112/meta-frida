project('frida-gumjs-smoketest', 'c', version: '1.0')

gumjs = dependency('frida-gumjs-1.0', static: true, required: true)

executable('frida-gumjs-smoketest', 'main.c',
  dependencies: gumjs,
  install: true,
)
