# -*- coding: utf-8 -*-

from setuptools import setup


with open('README.rst') as f:
    readme = f.read()

with open('LICENSE') as f:
    license = f.read()

setup(
    name='pyano',
    version='0.1.0',
    description='Basic piano emulation',
    long_description=readme,
    author='FelixGSE',
    author_email='',
    url='https://github.com/FelixGSE/pyano',
    license=license,
    packages=['pyano'],
    package_dir={'pyano': 'pyano'},
    package_data={'pyano': ['sound_fonts/*']},
    install_requires=[
      "mingus==0.6.1",
      "numpy==1.20.2",
      "sf2utils==0.9.0",
      "requests==2.25.1"
     ]
)

