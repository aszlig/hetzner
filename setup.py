#!/usr/bin/env python
import os
import sys

from distutils.core import setup, Command

PYTHON_MODULES = [
    'hetzner',
    'hetzner.rdns',
    'hetzner.robot',
    'hetzner.server',
    'hetzner.util',
]


class RunTests(Command):
    description = "run test suite"
    user_options = []
    initialize_options = finalize_options = lambda self: None

    def run(self):
        from doctest import testmod
        for module in PYTHON_MODULES:
            modpath = os.path.join(*module.split('.'))
            package, name = os.path.split(modpath)
            sys.path.insert(0, package)
            imported = __import__(name)
            del sys.path[0]
            failures, _ = testmod(imported, report=True)
            if failures > 0:
                raise SystemExit(1)

setup(name='hetzner',
      version='0.7.0',
      description='High level access to the Hetzner robot',
      url='https://github.com/RedMoonStudios/hetzner',
      author='aszlig',
      author_email='aszlig@redmoonstudios.org',
      scripts=['hetznerctl'],
      py_modules=PYTHON_MODULES,
      cmdclass={'test': RunTests},
      license='BSD')
