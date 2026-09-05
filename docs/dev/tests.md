(dev-testing)=
# Manual and CI/CD Testing

*netlab* uses a GitHub Actions CI/CD pipeline with multiple workflows. The automated tests executed on every push or pull request include:

* **mypy** static type checking of all Python code in `netsim/` directory
* **ruff** linting of all Python code
* **yamllint** validation of all YAML files in `netsim/` and `tests/` directories
* Transformation tests and error-case tests run with **pytest** in `tests/` directory
* Integration-test topology validation (`netlab create -d none`) for fork PRs

You can run the same tests locally in the *tests* directory. It's highly recommended that you run them before creating a pull request that modifies Python code. PRs that fail the CI/CD pipeline will not be merged.

```{tip}
* The CI/CD tests require additional Python modules. Install them with `pip3 install -r requirements-dev.txt`
* The CI/CD tests use PyYAML. You can run them on a system with `ruamel.yaml` installed, but they might take longer (see [bug report](https://github.com/ipspace/netlab/issues/3345) and [related PR](https://github.com/ipspace/netlab/pull/3353) for details). Uninstalling `ruamel.yaml` might not be a bad idea. 
```

```eval_rst
.. contents:: Table of Contents
   :depth: 2
   :local:
   :backlinks: none
```

## Before Submitting a PR

If your PR includes modifications to Python code:

* Run the `run-tests.sh` script in the `tests` directory to run the [automated tests](dev-testing-auto) that will be run as part of the CI/CD pipeline (see also [](dev-testing-runners))
* If the tests fail, your code modifications changed the data transformation logic or error messages.
* If you're absolutely sure your changes are correct, run the `create-transformation-tests.sh` and `create-error-tests.sh` scripts in the `tests` directory to recreate the expected test results.
* Check the differences between previous and new expected test results.
* Add modified test results to your commit.

```{tip}
Automated CI/CD tests will check your expected test results anyway, and we'll have a discussion if you submit "suboptimal" content ;)
```

When modifying documentation:

* Test the [documentation changes](dev-testing-docs)

When modifying device templates or adding new device functionality:

* Run the relevant [integration tests](dev-testing-integration). 
* If possible, add the integration test results to the PR.

Finally: 

* Submit a PR.
* The PR should be in *draft* state when you're still working on it and in *ready for review* state when you're done.
* Ask someone to review your code. GitHub is pretty good at identifying who worked on the code recently; that person might be your best bet.

(dev-testing-auto)=
## Automated Tests

The **test_transformation.py** test harness runs three types of transformation tests:

* Regular transformations (see below)
* Error cases -- topologies that should generate an error resulting in an aborted transformation attempt. Add tests to this directory only when you need to test error messages in the Python code.
* Verbose test cases -- identical to regular transformations but with more logging. Used only when measuring code coverage (to ensure all logging printouts are triggered)

(dev-testing-runners)=
### Test Runner Scripts

The `tests/` directory contains several shell scripts to run subsets of the test suite:

| Script | Command | Purpose |
|---|---|---|
| `run-tests.sh` | `mypy` + `pytest -v -k 'xform_ or error_cases'` + `yamllint` | **Main CI/CD suite**. Accepts `ci` argument for fail-fast mode (`set -e`). |
| `run-xform.sh` | `pytest -v -k xform_` | Transformation tests only |
| `run-xerr.sh` | `pytest -v -k error_cases` | Error tests only |
| `run-yamllint.sh` | `yamllint --no-warnings` on `netsim/` and `tests/` | Standalone YAML linting |
| `run-typing.sh` | `mypy --no-incremental -p netsim` | Standalone type checking |
| `run-coverage-tests.sh` | `pytest -v -k 'coverage'` | Coverage tests only (see [coverage tests](dev-testing-coverage)) |

You can run any of these scripts from the `tests` directory. For example:

```bash
$ cd tests
$ ./run-tests.sh ci        # Full CI/CD suite with fail-fast
$ ./run-xform.sh           # Transformation tests only
$ ./run-coverage-tests.sh  # Coverage tests only
```

(dev-testing-xform)=
### Data Transformation Tests

The regular transformation tests:

* Take a topology file from *tests/topology/input* directory
* Run the transformation code
* Render the resulting data structure (without address pools or system defaults) in YAML format
* Compare the results with corresponding file from *tests/topology/expected* directory

Whenever you're creating a new test case or modifying an existing one, you **HAVE TO** create a corresponding *expected results* file. Please don't try to create the expected results by hand -- the results are compared as strings, not data structures, and it's just not worth the effort to fix them manually.

To create *expected results* files, run the `create-transformation-tests.sh` script in the *tests* directory. The script assumes your code works flawlessly and that whatever it does is the correct result. That might *not* be the case, so it's highly recommended that you execute `git diff topology` after running the `create-transformation-tests.sh` script and do a thorough check of the differences.

(dev-testing-errmsg)=
### Transformation Error Tests

The transformation error tests:

* Take a `.yml` topology file from the *tests/errors* directory
* Run the transformation code that should result in a 'fatal error' exit
* Collect the error messages generated during the data transformation
* Compare the collected error messages with the corresponding `.log` file from *tests/errors* directory

Whenever you're creating a new error test case or modifying an existing one, you **HAVE TO** create a corresponding *expected error messages* log file.

To create the *expected error messages* files, run the `create-error-tests.sh` script in the *tests* directory. The script assumes your code works flawlessly and that any generated error messages are the expected error messages. That might *not* be the case, so it's highly recommended that you execute `git diff errors` after running the `create-errors-tests.sh` script and do a thorough check of the differences.

```{warning}
You cannot create a new error test on a system with `ruamel.yaml` package (details in the [bug report](https://github.com/ipspace/netlab/issues/3345) and [related PR](https://github.com/ipspace/netlab/pull/3353)). Uninstall `ruamel.yaml` before running the `create-error-tests.sh` script.
```

(dev-testing-coverage)=
### Coverage Tests

Coverage tests ensure edge cases and rarely exercised code paths are covered. They are stored separately from the main test fixtures:

* **Coverage transformation tests** (`tests/coverage/input/` → `tests/coverage/expected/`): Edge cases not in the main set -- dict-key types, empty links, invalid attributes, defaults inheritance, unnumbered edge cases, and more.
* **Coverage error tests** (`tests/coverage/errors/`): Attribute/type validation errors, group errors, node validation, and similar edge cases.
* **Verbose coverage tests**: Re-run the main transformation test cases with verbose logging while coverage measurement is active. These only execute under a trace (i.e., when `coverage run` is active), ensuring all logging printouts are triggered.

#### Running Coverage Tests

To run coverage tests only (without coverage measurement):

```bash
$ cd tests
$ ./run-coverage-tests.sh
```

To generate a full HTML coverage report:

```bash
$ cd tests
$ ./coverage.sh
```

This uses the `coverage` package (not pytest-cov) to instrument the code, then generates an HTML report in `tests/htmlcov/`. The `.coverage` and `htmlcov/` directories are gitignored.

```{tip}
The coverage report shows which lines of Python code in `netsim/` are executed during the test suite. Use it to identify untested code paths that need new test fixtures.
```

#### Creating Coverage Test Fixtures

To regenerate the expected *coverage test* results:

```bash
$ cd tests
$ ./create-transformation-tests.sh coverage   # Regenerate coverage transformation expected files
$ ./create-error-tests.sh coverage            # Regenerate coverage error expected files
```

```{warning}
As with the main error tests, `create-error-tests.sh coverage` refuses to run if `ruamel.yaml` is installed.
```

(dev-testing-docs)=
## Testing Documentation Changes

*netlab* documentation is built with Sphinx. You can generate and inspect the HTML output locally before submitting a PR.

### Prerequisites

From the repository root directory, install the documentation build dependencies:

```bash
pip3 install -r docs/requirements.txt
```

This installs Sphinx, the MyST parser, the Read the Docs theme, and other required packages. The `docs/requirements.txt` file pins specific versions to ensure consistent CI/CD builds.

### Building HTML Documentation

From the `docs` directory, run:

```bash
make html
```

This invokes `sphinx-build` and writes the generated HTML files to `_build/html/`.

_netlab_ documentation uses Sphinx extensions that rely on _netsim_ modules to fetch default settings. The documentation build process might fail if you don't have the GitHub repository in the Python path. In that case, use:

```bash
PYTHONPATH=.. make html
```

Sphinx will report warnings for broken links, missing references, or markup errors during the build -- fix these before submitting a PR.

```{tip}
Run `make clean html` to do a full rebuild, avoid stale cached pages, and detect broken links in pages you haven't modified.
```

### Inspecting the Result

From the `docs` directory, open the top-level HTML page in your browser:

```bash
open _build/html/index.html          # macOS
xdg-open _build/html/index.html      # Linux
```

Browse the pages you modified.

(dev-testing-integration)=
## Integration Tests

[Integration tests](integration-testing) are run by hand; it's too much hassle to set up an automated test environment with vendor boxes/containers/license files. The latest results are available at [https://tests.netlab.tools/](https://tests.netlab.tools/).

The test topologies are stored in the `tests/integration` directory. If you're adding new device features or changing device configuration templates, please [run the relevant tests](integration-test-suite) before submitting a PR.

Most integration tests include automated validation. The easiest way to use automated validation with a single test is to [run](integration-test-single) the `netlab up _test_scenario_ --validate` command.

### Integration Test Topology Validation

On every pull request, the CI/CD pipeline runs `check-integration-tests.sh`, which validates all integration test topologies by executing `netlab create -o none -d none` against every numbered test file in `tests/integration/` and `tests/platform-integration/`. This ensures that the topology transformation code does not break any integration test definitions.

## Background: GitHub Actions Workflows

The CI/CD pipeline consists of the following workflows in `.github/workflows/`:

| Workflow | Trigger | Purpose |
|---|---|---|
| `t-push.yml` | Push to any branch (except `devc`) when `**.py` or `**.yml` change | Runs **mypy** and full **pytest** suite across Python 3.10, 3.13, and 3.14 |
| `t-pull.yml` | Pull request touching `**.py` or `**.yml` | Runs mypy + pytest (forks only), then **integration-test topology validation** (`check-integration-tests.sh`) for all PRs |
| `t-yamllint.yml` | Push (non-`devc`) / PR on `**.yml` | Runs `yamllint --no-warnings` on all YAML in `netsim/` and `tests/` |
| `ruff.yml` | Push (non-`devc`) / PR on `**.py`, `ruff.toml`, or the workflow file | Runs `ruff check --output-format=github .` on Python 3.14 |
| `integration.yml` | GitHub issue comment containing `/integration` | Runs real integration tests on a **self-hosted runner** with vendor boxes/containers |
| `pages.yml` | Push to `master` or manual dispatch | Builds Sphinx docs and deploys to GitHub Pages |
| `pypi.yml` | Push of `release_*` tag | Builds and publishes package to PyPI |
| `test-pypi.yml` | Completion of "Run CICD Tests" on `dev`/`cicd-fix` branches | Builds and publishes to Test PyPI |
| `devcontainer-*.yml` | Various | Builds and pushes devcontainer images |

### What Happens on a Push or PR

1. **`t-push.yml`** (push) / **`t-pull.yml`** (PR) runs the full test matrix:
   * Installs `requirements.txt` and `requirements-dev.txt`
   * Runs `mypy -p netsim` (type checking)
   * Runs `cd tests && PYTHONPATH="../" pytest` (all transformation and error tests)
   * For PRs from forks, also runs `check-integration-tests.sh` (validates all integration topologies with `-d none`)
2. **`t-yamllint.yml`** lints all YAML files
3. **`ruff.yml`** lints all Python files

```{tip}
The push and pull-request workflows run on a matrix of Python 3.10, 3.13, and 3.14. The ruff workflow runs on Python 3.14 only.
```

