# Automated CI/CD Tests

*netlab* uses GitHub Workflows CI/CD pipeline, see `.github/workflows/tests.yml` for details. The automated tests executed on every push, pull request or merge include:

* **mypy** static type checking of all Python code in `netsim/` directory
* Transformation tests ran with **pytest** in `tests/` directory

You can run the same tests with the `run-tests.sh` script in *tests* directory. It's highly recommended you run them before creating a pull request that modifies Python code, or we'll have to have a discussion before your PR is merged.

## Transformation Tests

The **test_transformation.py** test harness runs three types of transformation tests:

* Regular transformations (see below)
* Error cases -- topologies that should generate an error resulting in an aborted transformation attempt. Add tests to this directory only when you need to test error messages in the Python code.
* Minimal test cases -- low level topologies (without system defaults) that should generate hard-to-reproduce errors (because system defaults shouldn't allow them to happen). Please don't create new minimal test cases; if you need a test case without system defaults, use **include: []** top-level element (example in `topology/input/addrs-no-pool.yml`)

The regular transformation tests:

* Take a topology file from *tests/topology/input* directory
* Run the transformation code
* Render the resulting data structure (without address pools or system defaults) in YAML format
* Compare the results with corresponding file from *tests/topology/expected* drectory

Whenever you're creating a new test case or modifying an existing one, you **HAVE TO** create a corresponding *expected results* file. Please don't try to create the expected results by hand -- the results are compared as strings, not data structures, and it's just not worth the effort to fix them manually.

To create *expected results* files run `create-transformation-tests.sh` script in the *tests* directory. The script assumes that your code works flawlessly and that whatever the code does is the correct result. That might *not* be the case, so it's highly recommended that you execute `git diff topology` after running `create-transformation-tests.sh` script and do a thorough check of the differences.

## Before Submitting a PR

If you PR includes modifications to Python code, make sure you follow these steps before submitting it:

* Run `create-transformation-tests.sh` script
* Check the differences (again)
* Add modified *tests/topology/expected* files to your commit
* Submit a PR

```{tip}
Someone will check your expected test results and we'll have a discussion if you submit "suboptimal" content ;)
```

## Integration Tests

Integration tests are ran by hand -- it's too much hassle to set up an automated test environment with vendor boxes/containers/license files. The test topologies are stored in *tests/integration* directory.
