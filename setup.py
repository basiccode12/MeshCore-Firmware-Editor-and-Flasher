#!/usr/bin/env python3
"""
Setup script for Meshcore Firmware Editor and Flasher
"""

from setuptools import setup, find_packages
import os

# Read the README file for long description
readme_path = os.path.join(os.path.dirname(__file__), 'README.md')
long_description = ""
if os.path.exists(readme_path):
    with open(readme_path, 'r', encoding='utf-8') as f:
        long_description = f.read()

setup(
    name='meshcore-firmware-editor',
    version='1.0.0',
    description='A simple GUI tool for editing and flashing MeshCore firmware',
    long_description=long_description,
    long_description_content_type='text/markdown',
    author='MeshCore',
    url='https://github.com/meshcore-dev/MeshCore',
    license='MIT',
    py_modules=['meshcore_flasher'],
    packages=find_packages(),
    python_requires='>=3.6',
    install_requires=[
        # No external dependencies - uses only standard library
    ],
    entry_points={
        'console_scripts': [
            'meshcore-firmware-editor=meshcore_flasher:main',
        ],
    },
    classifiers=[
        'Development Status :: 4 - Beta',
        'Intended Audience :: Developers',
        'License :: OSI Approved :: MIT License',
        'Programming Language :: Python :: 3',
        'Programming Language :: Python :: 3.6',
        'Programming Language :: Python :: 3.7',
        'Programming Language :: Python :: 3.8',
        'Programming Language :: Python :: 3.9',
        'Programming Language :: Python :: 3.10',
        'Programming Language :: Python :: 3.11',
        'Operating System :: OS Independent',
    ],
)

