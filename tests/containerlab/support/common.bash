_common() {
  load 'support/bats-support/load'
  load 'support/bats-assert/load'

  # Get the containing directory of this file
  # use $BATS_TEST_FILENAME instead of ${BASH_SOURCE[0]} or $0,
  # Those point to the bats executable location (${BASH_SOURCE[0]}) or
  # the preprocessed file ($0)
  TOOLS="$( cd "$( dirname "$BATS_TEST_FILENAME" )/../.." >/dev/null 2>&1 && pwd )"
  # make executables in repo visible to PATH
  PATH="$TOOLS:$PATH"

  rm -fr host_vars group_vars


}
