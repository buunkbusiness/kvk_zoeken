from setuptools import setup, find_packages

with open("requirements.txt") as f:
	install_requires = f.read().strip().split("\n")

# get version from __version__ variable in kvk_zoeken/__init__.py
from kvk_zoeken import __version__ as version

setup(
	name="kvk_zoeken",
	version=version,
	description="Integration with the KVK API for searching and creating relations",
	author="Buunk Business",
	author_email="admin@buunkbusiness.nl",
	packages=find_packages(),
	zip_safe=False,
	include_package_data=True,
	install_requires=install_requires
)