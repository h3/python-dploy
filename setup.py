# -*- coding: utf-8 -*-

import os

from setuptools import setup, find_packages


def read(fname):
    return open(os.path.join(os.path.dirname(__file__), fname)).read()

setup(
    name='dploy',
    version='0.0.1',
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
    install_requires=[
        'PyYAML>=3.12',
        'Jinja2>=2.9.5',
        'Fabric>=1.14.0',
        'docopt>=0.6.2',
        'fabtools>=0.20.0',
    ],
    classifiers=[
        'Environment :: Console',
        'Intended Audience :: Developers',
        'License :: OSI Approved :: MIT License',
        'Operating System :: OS Independent',
        'Programming Language :: Python',
    ]
)
