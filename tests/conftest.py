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
# 4. Normalize the failure-report "reprcrash" message to its first line so
#    pytest's `short test summary info` does not duplicate the diff body
#    that `_report_mismatch` puts in the `pytest.fail(...)` message. The
#    rich multi-line message stays in `longrepr`, so the `FAILURES`
#    section is unaffected. Without this, pytest 9.x prints the entire
#    failure message verbatim in the short summary whenever it detects
#    CI (`CI`/`BUILD_NUMBER` env vars) or runs at `-vv`+ -- see
#    `_pytest/terminal.py::_get_line_with_reprcrash_message`. Pytest's
#    own `ReprFileLocation.toterminal` already trims to the first line;
#    we just enforce the same invariant globally.
#

import os
import pathlib
import sys
import typing

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


@pytest.hookimpl(hookwrapper=True)
def pytest_runtest_makereport(item: pytest.Item, call: pytest.CallInfo[None]) -> typing.Generator[None, None, None]:
  outcome = yield
  report = outcome.get_result()  # type: ignore[attr-defined]
  crash = getattr(getattr(report, "longrepr", None), "reprcrash", None)
  if crash is not None and "\n" in crash.message:
    crash.message = crash.message.split("\n", 1)[0]
