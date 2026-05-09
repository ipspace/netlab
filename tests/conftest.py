#
# Pytest hooks shared across the netlab test tree
#

import pytest
from utils import HAS_RUAMEL


def pytest_configure(config: pytest.Config) -> None:
  if not HAS_RUAMEL:
    return
  config.issue_config_time_warning(
    UserWarning(
      "ruamel.yaml is installed; transformation tests will be slower and "
      "`create-error-tests.sh` is unsupported "
      "(see https://github.com/ipspace/netlab/issues/3345)."
    ),
    stacklevel=2,
  )
