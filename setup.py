#!/usr/bin/env python

import codecs
import os
import re
from mark_version import VERSION_NUM

from setuptools import setup, find_packages
try: # for pip >= 10
    from pip._internal.req import parse_requirements
except ImportError: # for pip <= 9.0.3
    from pip.req import parse_requirements


NAME = 'snap'
VERSION = VERSION_NUM
PACKAGES = find_packages(where='.', exclude='tests')
DEPENDENCIES=['docopt',
              'Flask',
              'flask-cors',
              'itsdangerous',
              'Jinja2',
              'MarkupSafe',
              'PyYAML',
              'Werkzeug',
              'requests']

def read(fname):
    return open(os.path.join(os.path.dirname(__file__), fname)).read()


setup(
    name='snap-micro',
    version=VERSION,
    author='Dexter Taylor',
    author_email='binarymachineshop@gmail.com',
    platforms=['any'],
    scripts=['scripts/routegen', 'scripts/uwsgen', 'scripts/snapconfig', 'scripts/snap-version'],
    packages=find_packages(),
    install_requires=DEPENDENCIES,
    include_package_data=True,
    test_suite='tests',
    description=('Small Network Applications in Python: a microservices toolkit'),
    license='MIT',
    keywords='microservices web framework',
    url='http://github.com/binarymachines/snap',
    long_description=read('README.txt'),
    classifiers=[
        'Development Status :: 4 - Beta',
        'License :: OSI Approved :: MIT License',
        'Programming Language :: Python',
        'Topic :: Software Development'
    ]
)
