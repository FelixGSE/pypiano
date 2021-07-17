# -*- coding: utf-8 -*-
from setuptools import setup
import requests

with open('./pypiano/sound_fonts/FluidR3_GM.sf2', 'w') as f:
    response = requests.get('https://github.com/FelixGSE/pypiano/raw/master/pypiano/sound_fonts/FluidR3_GM.sf2')
    f.write(response.content)
    
with open("README.md") as f:
    readme = f.read()

with open("requirements.txt") as f:
    requirements = f.read()

setup(
    name="pypiano",
    version="0.1.0",
    description="Library to programmatically play piano",
    long_description=readme,
    long_description_content_type="text/markdown",
    author="FelixGSE",
    author_email="",
    url="https://github.com/FelixGSE/pypiano",
    license="MIT",
    packages=["pypiano"],
    package_dir={"pypiano": "pypiano"},
    package_data={"pypiano": ["sound_fonts/*"]},
    install_requires=requirements,
)
