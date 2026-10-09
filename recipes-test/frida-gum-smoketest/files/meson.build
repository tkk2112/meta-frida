project('frida-gum-smoketest', 'c', version: '1.0')

gum = dependency('frida-gum-1.0', static: true, required: true)

executable('frida-gum-smoketest', 'main.c',
  dependencies: gum,
  install: true,
)
