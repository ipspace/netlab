"""setup.py file."""
from setuptools import setup, find_packages

with open("requirements.txt", "r") as fs:
  reqs = [r for r in fs.read().splitlines() if (len(r) > 0 and not r.startswith("#"))]

setup(
  name="netsim-tools",
  version="0.8.1",
  packages=find_packages(),
  author="Ivan Pepelnjak",
  author_email="ip@ipspace.net",
  description="CLI-based Virtual Networking Lab Abstraction Layer",
  classifiers=[
    "Topic :: Utilities",
    "Programming Language :: Python",
    "Programming Language :: Python :: 3",
    "Programming Language :: Python :: 3.9",
    "Operating System :: POSIX :: Linux",
    "Operating System :: MacOS",
  ],
  url="https://github.com/ipspace/netsim-tools",
  include_package_data=True,
  setup_requires=["wheel"],
  install_requires=reqs,
  entry_points={
    "console_scripts": ["netlab=netsim.cli:lab_commands"]
  },
  package_data = {
    "netsim": ["templates/*", "../ansible/*"]
  }
)