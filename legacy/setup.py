""" redirect netsim-tools to networklab """
import sys
from pathlib import Path

from setuptools import setup

sys.path.append('..')

version="25.11.01"

long_description = (Path(__file__).parent / "README.md").read_text()

setup(
  name="netsim-tools",
  version=version,
  packages=[],
  author="Ivan Pepelnjak",
  author_email="ip@ipspace.net",
  description="CLI-based Virtual Networking Lab Abstraction Layer",
  long_description=long_description,
  install_requires=[f"networklab>={version}"],
  classifiers=[
    "Topic :: Utilities",
    "Programming Language :: Python",
    "Programming Language :: Python :: 3",
    "Programming Language :: Python :: 3.9",
    "Programming Language :: Python :: 3.10",
    "Programming Language :: Python :: 3.11",
    "Programming Language :: Python :: 3.12",
    "Operating System :: POSIX :: Linux",
    "Operating System :: MacOS",
  ],
  url="https://github.com/ipspace/netlab",
  python_requires='>=3.8',  # Due to e.g. 'capture_output' in subprocess.run
)
