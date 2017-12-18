#!/usr/bin/env python

import codecs
import os
import re

from setuptools import setup, find_packages
from pip.req import parse_requirements
from pip.download import PipSession


NAME = 'snap'
VERSION = '0.9.52'
PACKAGES = find_packages(where='src')
DEPENDENCIES=['docopt',
              'Flask',
              'itsdangerous',
              'Jinja2',
              'MarkupSafe',
              'PyYAML',
              'SQLAlchemy',
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
    scripts=['scripts/routegen', 'scripts/uwsgen', 'scripts/snapconfig'],
    packages=find_packages(),
    install_requires=DEPENDENCIES,
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
