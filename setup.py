# -*- coding: utf-8 -*-
from setuptools import setup, find_packages

setup(
    name='gotorrent',
    version='0.0.1',
    url='https://github.com/Willyn/GoTorrent',
    license='MIT License',
    author='Adrian Gutierrez, Gerard Gonzalez',
    install_requires=['gevent', 'pyactor'],
    test_suite='test',
)