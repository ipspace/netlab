#!/usr/bin/env python3
#
# Tests for the netlab CLI commands
#

from unittest import mock

import pytest

from netsim.cli import test as cli_test
from netsim.utils import log


def test_cleanup_force_aborted_by_user() -> None:
  log.init_log_system(header = False)
  log.set_flag(raise_error = True)

  with mock.patch('builtins.input',side_effect=KeyboardInterrupt):
    with pytest.raises(log.ErrorAbort):
      cli_test.cleanup_force()
