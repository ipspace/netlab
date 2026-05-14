#
# Shared pytest configuration for the netlab test suite.
#
# 1. Prepend the repository root (the directory containing the 'netsim'
#    package) to sys.path so 'cd tests && pytest' inside a git worktree
#    imports this checkout's netsim/, not the venv egg-link's (which
#    usually points at the main checkout).
#
# 2. Anchor the working directory to tests/ so the test bodies' relative
#    globs (e.g. glob.glob('topology/input/*yml')) resolve no matter
#    where pytest is invoked from.
#
# 3. Surface a UserWarning when ruamel.yaml is installed -- the
#    transformation tests will be slower and create-error-tests.sh is
#    unsupported (see https://github.com/ipspace/netlab/issues/3345).
#

import os
import pathlib
import sys

import pytest

_HERE = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(_HERE.parent))

from utils import HAS_RUAMEL  # noqa: E402 -- requires sys.path tweak above


def pytest_configure(config: pytest.Config) -> None:
  os.chdir(_HERE)
  if HAS_RUAMEL:
    config.issue_config_time_warning(
      UserWarning(
        "ruamel.yaml is installed; transformation tests will be slower and "
        "`create-error-tests.sh` is unsupported "
        "(see https://github.com/ipspace/netlab/issues/3345)."
      ),
      stacklevel=2,
    )
