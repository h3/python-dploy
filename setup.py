# -*- coding: utf-8 -*-

import os

from setuptools import setup


def read(fname):
    return open(os.path.join(os.path.dirname(__file__), fname)).read()

setup(
    name='fabric-contrib-dploy',
    version='0.0.1',
    description='Deployment utilities for fabric',
    long_description=(read('README.rst')),
    author='Maxime Haineault',
    author_email='haineault@gmail.com',
    license='MIT',
    url='https://github.com/h3/fabric-contrib-dploy',
    packages=['fabric.contrib.dploy'],
    include_package_data=True,
    zip_safe=True,
    classifiers=[
        'Environment :: Console',
        'Intended Audience :: Developers',
        'License :: OSI Approved :: MIT License',
        'Operating System :: OS Independent',
        'Programming Language :: Python',
    ]
)
