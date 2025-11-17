"""setup.py file."""
import sys
from pathlib import Path

from setuptools import find_packages, setup

import netsim

long_description = (Path(__file__).parent / "README.md").read_text()

with open("requirements.txt", "r") as fs:
  reqs = [r for r in fs.read().splitlines() if (len(r) > 0 and not r.startswith("#"))]

if sys.version_info < (3, 8):
  raise RuntimeError("This package requires Python 3.8+")

setup(
  name="networklab",
  version=netsim.__version__,
  packages=find_packages(),
  author="Ivan Pepelnjak",
  author_email="ip@ipspace.net",
  description="CLI-based Virtual Networking Lab Abstraction Layer",
  long_description=long_description,
  long_description_content_type='text/markdown',
  classifiers=[
    "Topic :: Utilities",
    "Programming Language :: Python",
    "Programming Language :: Python :: 3",
    "Programming Language :: Python :: 3.8",
    "Programming Language :: Python :: 3.9",
    "Programming Language :: Python :: 3.10",
    "Programming Language :: Python :: 3.11",
    "Programming Language :: Python :: 3.12",
    "Programming Language :: Python :: 3.13",
    "Programming Language :: Python :: 3.14",
    "Operating System :: POSIX :: Linux",
    "Operating System :: MacOS",
  ],
  url="https://github.com/ipspace/netlab",
  include_package_data=True,
  setup_requires=["wheel"],
  python_requires='>=3.8',  # Due to e.g. 'capture_output' in subprocess.run, and use of typing.Final
  install_requires=reqs,
  scripts=[ "netlab" ],
#  entry_points={
#    "console_scripts": ["netlab=netsim.cli:lab_commands"]
#  },
  package_data = {
    "netsim": ["templates/*", "ansible/*", "extra/*", "reports/*", "install/*"],
  }
)
