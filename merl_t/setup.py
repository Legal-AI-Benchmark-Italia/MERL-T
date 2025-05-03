#!/usr/bin/env python3
"""
Setup script for MERL-T package.
"""

from setuptools import setup, find_packages
import os

# Read requirements from requirements.txt
with open("requirements.txt") as f:
    requirements = f.read().splitlines()

# Read version from __init__.py
version = {}
with open(os.path.join("src", "__init__.py")) as f:
    exec(f.read(), version)

# Read README for long description
with open("README.md", encoding="utf-8") as f:
    long_description = f.read()

setup(
    name="merl-t",
    version=version.get("__version__", "0.1.0.dev"),
    description="Multi-Expert Retrieval Legal Transformer",
    long_description=long_description,
    long_description_content_type="text/markdown",
    author="LAIBIT Community",
    author_email="info@laibit.it",
    url="https://github.com/laibit/merl-t",
    packages=find_packages(),
    package_data={
        "src": ["py.typed"],
    },
    entry_points={
        "console_scripts": [
            "merl-t-server=src.server:main",
        ],
    },
    install_requires=requirements,
    classifiers=[
        "Development Status :: 3 - Alpha",
        "Intended Audience :: Developers",
        "Intended Audience :: Legal Industry",
        "License :: OSI Approved :: MIT License",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
        "Topic :: Scientific/Engineering :: Artificial Intelligence",
        "Topic :: Text Processing :: Linguistic",
    ],
    python_requires=">=3.8",
) 