#!/usr/bin/env python
from distutils.core import setup

setup(name='hetzner',
      version='0.7.5',
      description='High level access to the Hetzner robot',
      url='https://github.com/RedMoonStudios/hetzner',
      author='aszlig',
      author_email='aszlig@redmoonstudios.org',
      scripts=['hetznerctl'],
      py_modules=['hetzner', 'hetzner.robot', 'hetzner.server'],
      license='BSD')
