# -*- coding: utf-8 -*-

import os

from setuptools import setup, find_packages

import sys

VERSION = '0.1.0'

dependency_links = []
install_requires = [
    'PyYAML>=3.12',
    'Jinja2>=2.9.5',
    'docopt>=0.6.2',
]

if sys.version_info.major < 3:
    # py2
    install_requires.append('Fabric>=1.14.0')
    install_requires.append('fabtools>=0.20.0')
else:
    # py3
    install_requires.append('Fabric3==1.13.1.post1')
    install_requires.append('fabtools==0.20.0')
    dependency_links = [
        "git+ssh://git@github.com/h3/fabtools.git@python3#egg=fabtools-0.20.0",
    ]


def read(fname):
    return open(os.path.join(os.path.dirname(__file__), fname)).read()

setup(
    name='dploy',
    version=VERSION,
    description='Deployment utilities for fabric',
    long_description=(read('README.md')),
    author='Maxime Haineault',
    author_email='haineault@gmail.com',
    license='MIT',
    url='https://github.com/h3/fabric-contrib-dploy',
    packages=find_packages(),
    include_package_data=True,
    zip_safe=True,
    scripts=['dploy/bin/python-dploy'],
    install_requires=install_requires,
    dependency_links=dependency_links,
    classifiers=[
        'Environment :: Console',
        'Intended Audience :: Developers',
        'License :: OSI Approved :: MIT License',
        'Operating System :: OS Independent',
        'Programming Language :: Python',
    ]
)
