(dev-testing)=
# Manual and CI/CD Testing

*netlab* uses GitHub Workflows CI/CD pipeline; see `.github/workflows/tests.yml` for details. The automated tests executed on every push, pull request, or merge include:

* **mypy** static type checking of all Python code in `netsim/` directory
* Transformation tests ran with **pytest** in `tests/` directory

You can run the same tests with the `run-tests.sh` script in *tests* directory. It's highly recommended that you run them before creating a pull request that modifies Python code. PRs that fail the CI/CD pipeline will not be merged.

```{tip}
* The CI/CD tests require additional Python modules. Install them with `pip3 install -r requirements-dev.txt`
* The CI/CD tests use PyYAML. You can run them on a system with `ruamel.yaml` installed, but they might take longer (see [bug report](https://github.com/ipspace/netlab/issues/3345) and [related PR](https://github.com/ipspace/netlab/pull/3353) for details). Uninstalling `ruamel.yaml` might not be a bad idea. 
```

## Before Submitting a PR

If your PR includes modifications to Python code:

* Run the `run-tests.sh` script in the `tests` directory to run the [automated tests](dev-testing-auto) that will be run as part of the CI/CD pipeline.
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

(dev-testing-xform)=
### Data Transformation Tests

The regular transformation tests:

* Take a topology file from *tests/topology/input* directory
* Run the transformation code
* Render the resulting data structure (without address pools or system defaults) in YAML format
* Compare the results with corresponding file from *tests/topology/expected* directory

Whenever you're creating a new test case or modifying an existing one, you **HAVE TO** create a corresponding *expected results* file. Please don't try to create the expected results by hand -- the results are compared as strings, not data structures, and it's just not worth the effort to fix them manually.

To create *expected results* files run `create-transformation-tests.sh` script in the *tests* directory. The script assumes that your code works flawlessly and that whatever the code does is the correct result. That might *not* be the case, so it's highly recommended that you execute `git diff topology` after running `create-transformation-tests.sh` script and do a thorough check of the differences.

(dev-testing-errmsg)=
### Transformation Error Tests

The transformation error tests:

* Take a `.yml` topology file from the *tests/errors* directory
* Run the transformation code that should result in a 'fatal error' exit
* Collect the error messages generated during the data transformation
* Compare the collected error messages with the corresponding `.log` file from *tests/errors* directory

Whenever you're creating a new error test case or modifying an existing one, you **HAVE TO** create a corresponding *expected error messages* log file.

To create the *expected error messages* files, run the `create-error-tests.sh` script in the *tests* directory. The script assumes that your code works flawlessly and that whatever error messages are generated are the expected error messages. That might *not* be the case, so it's highly recommended that you execute `git diff errors` after running the `create-errors-tests.sh` script and do a thorough check of the differences.

```{warning}
You cannot create a new error test on a system with `ruamel.yaml` package (details in the [bug report](https://github.com/ipspace/netlab/issues/3345) and [related PR](https://github.com/ipspace/netlab/pull/3353)). Uninstall `ruamel.yaml` before running the `create-error-tests.sh` script.
```

(dev-testing-docs)=
## Testing Documentation Changes

*netlab* documentation is built with Sphinx. You can generate and inspect the HTML output locally before submitting a PR.

### Prerequisites

Install the documentation build dependencies:

```bash
pip3 install -r docs/requirements.txt
```

This installs Sphinx, the MyST parser, the Read the Docs theme, and other required packages. The `docs/requirements.txt` file pins specific versions to match the CI/CD builds.

### Building HTML Documentation

From the `docs` directory, run:

```bash
make html
```

This invokes `sphinx-build` and writes the generated HTML files to `docs/_build/html/`.

_netlab_ documentation uses Sphinx extensions that rely on _netsim_ modules to fetch default settings. The documentation build process might fail if you don't have the GitHub repository in the Python path. In that case, use:

```bash
PYTHONPATH=.. make html
```

### Inspecting the Result

Open the top-level page in your browser:

```bash
open docs/_build/html/index.html          # macOS
xdg-open docs/_build/html/index.html      # Linux
```

Browse the pages you modified. Sphinx will report warnings for broken links, missing references, or markup errors during the build -- fix these before submitting a PR.

```{tip}
Run `make clean html` to do a full rebuild, avoid stale cached pages, and detect broken links in pages you haven't modified.
```

(dev-testing-integration)=
## Integration Tests

[Integration tests](integration-testing) are run by hand; it's too much hassle to set up an automated test environment with vendor boxes/containers/license files. The latest results are available at [https://tests.netlab.tools/](https://tests.netlab.tools/).

The test topologies are stored in the `tests/integration` directory. If you're adding new device features or changing device configuration templates, please [run the relevant tests](integration-test-suite) before submitting a PR.

Most integration tests include automated validation. The easiest way to use automated validation with a single test is to [run](integration-test-single) the `netlab up _test_scenario_ --validate` command.
