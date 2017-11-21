#!/usr/bin/env python
import sys

from distutils.core import setup, Command
from unittest import TextTestRunner, TestLoader

PYTHON_MODULES = [
    'hetzner',
    'hetzner.failover',
    'hetzner.rdns',
    'hetzner.reset',
    'hetzner.robot',
    'hetzner.server',
    'hetzner.util',
    'hetzner.util.addr',
    'hetzner.util.http',
    'hetzner.util.scraping',
    'hetzner.tests',
    'hetzner.tests.test_util_addr',
]


class RunTests(Command):
    description = "run test suite"
    user_options = []
    initialize_options = finalize_options = lambda self: None

    def run(self):
        tests = TestLoader().loadTestsFromName('hetzner.tests')
        result = TextTestRunner(verbosity=1).run(tests)
        sys.exit(not result.wasSuccessful())


setup(name='hetzner',
      version='0.7.1',
      description='High level access to the Hetzner robot',
      url='https://github.com/RedMoonStudios/hetzner',
      author='aszlig',
      author_email='aszlig@redmoonstudios.org',
      scripts=['hetznerctl'],
      py_modules=PYTHON_MODULES,
      cmdclass={'test': RunTests},
      license='BSD')
