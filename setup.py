#!/usr/bin/env python2
from distutils.core import setup

setup(
    name = 'PNDstore',
    version = 'develop',
    description = 'Install and update PNDs',
    long_description = open('README.txt').read(),
    author = 'Randy Heydon',
    author_email = 'randy.heydon@clockworklab.net',
    url = 'https://github.com/Tempel/PNDstore',
    packages = ['pndstore', 'pndstore_gui'],
    package_data = {'pndstore': ['cfg/*']},
    scripts = ['wrapper.sh', 'PNDstore', 'pndst'],
    license = 'LGPL',
)
