#!/usr/bin/env python

import codecs
import os
import re

from setuptools import setup, find_packages


NAME = 'snap'
PACKAGES = find_packages(where='src')


def read(fname):
    return open(os.path.join(os.path.dirname(__file__), fname)).read()


setup(
    name='snap-micro',
    version='0.9.0',
    author='Dexter Taylor',
    author_email='binarymachineshop@gmail.com',
    platforms=['any'],
    packages=find_packages(),
    install_requires=[r.strip() for r in open('requirements.txt').readlines()],
    test_suite='tests',
    description=('Small Network Applications in Python: a microservices toolkit'),
    license='MIT',
    keywords='microservices web framework',
    url='http://packages.python.org/snap-micro',
    long_description=read('README.txt'),
    classifiers=[
        'Development Status :: 4 - Beta',
        'License :: OSI Approved :: MIT License',
        'Programming Language :: Python',
        'Topic :: Software Development'
    ]
)
