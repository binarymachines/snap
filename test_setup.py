#!/usr/bin/env python

import codecs
import os
import re

from setuptools import setup, find_packages
from pip.req import parse_requirements
from pip.download import PipSession

NAME = 'snap'
PACKAGES = find_packages(where='src')

install_reqs = parse_requirements('requirements.txt', session=PipSession())
reqs = [str(ir.req) for ir in install_reqs]
snap_version = os.getenv('SNAP_VERSION')
if not snap_version:
    raise Exception('The environment variable SNAP_VERSION has not been set.')

def read(fname):
    return open(os.path.join(os.path.dirname(__file__), fname)).read()


setup(
    name='snap-micro',
    version='%s' % snap_version,
    author='Dexter Taylor',
    author_email='binarymachineshop@gmail.com',
    platforms=['any'],
    scripts=['scripts/routegen', 'scripts/uwsgen', 'scripts/snapconfig'],
    packages=find_packages(),
    install_requires=reqs,                    
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
