# -*- coding: utf-8 -*-
from setuptools import setup

with open("README.md") as f:
    readme = f.read()

with open("requirements.txt") as f:
    requirements = f.read()

setup(
    name="pypiano",
    version="0.1.0",
    description="Library to programmatically play piano",
    long_description=readme,
    author="FelixGSE",
    author_email="",
    url="https://github.com/FelixGSE/pypiano",
    license="MIT",
    packages=["pypiano"],
    package_dir={"pypiano": "pypiano"},
    package_data={"pypiano": ["sound_fonts/*"]},
    install_requires=requirements,
)
