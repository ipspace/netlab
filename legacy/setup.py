""" redirect netsim-tools to networklab """
import sys
from setuptools import setup, find_packages

sys.path.append('..')

version="1.5.0"

setup(
  name="netsim-tools",
  version=version,
  packages=[],
  author="Ivan Pepelnjak",
  author_email="ip@ipspace.net",
  description="CLI-based Virtual Networking Lab Abstraction Layer",
  install_requires=[f"networklab>={version}"],
  classifiers=[
    "Topic :: Utilities",
    "Programming Language :: Python",
    "Programming Language :: Python :: 3",
    "Programming Language :: Python :: 3.9",
    "Operating System :: POSIX :: Linux",
    "Operating System :: MacOS",
  ],
  url="https://github.com/ipspace/netlab",
  python_requires='>=3.7',  # Due to e.g. 'capture_output' in subprocess.run
)

print("""
=======================================================================
                          WARNING WARNING WARNING
=======================================================================
netsim-tools has been renamed to netlab in August 2022.

The Python package netsim-tools has been renamed to networklab and is
installed as a dependency of netsim-tools every time you install or
upgrade netsim-tools, but we won't keep that dependency active foreer.

Please stop using netsim-tools package and use networklab package.
""")