# AGENTS.md - Guidelines for Agentic Coding Agents

This file contains build commands, code style guidelines, and development practices for agentic coding agents working in this netlab repository.

## Build/Lint/Test Commands

### Core Development Commands
```bash
# Type checking
python3 -m mypy -p netsim
python3 -m mypy netsim/extra/*/plugin.py  # Type check extra plugins

# Linting and formatting
ruff check netsim/          # Lint with ruff
ruff format netsim/         # Format with ruff

# YAML linting
yamllint netsim/*yml netsim/**/*yml tests/**/*yml

# Testing
python3 -m pytest -vvv -k 'xform_ or error_cases'    # Main test suite
python3 -m pytest -vvv -k 'coverage'                 # Coverage tests
python3 -m pytest tests/integration/                # Integration tests
python3 -m pytest tests/validation/                  # Validation tests

# Run single test file
python3 -m pytest -vvv tests/path/to/test_file.py

# Run tests with CI mode (fail fast)
cd tests && ./run-tests.sh ci
cd tests && ./run-coverage-tests.sh ci
```

### Installation and Setup
```bash
# Install dependencies
pip3 install -r requirements.txt
pip3 install -r requirements-dev.txt

# Install in development mode
pip3 install -e .
```

## Code Style Guidelines

### Import Organization
- Use `ruff` for import sorting (configured in ruff.toml)
- Standard library imports first, then third-party, then local imports
- Avoid wildcard imports except in `__init__.py` files

### Formatting Standards
- **Line length**: 120 characters (configured in ruff.toml)
- **Indentation**: 2 spaces (not tabs)
- **Quotes**: Double quotes for strings
- **Trailing commas**: Enabled for better diffs
- Align the comments

### Type Hints
- **Required**: All functions must have type hints (mypy enforces this)
- **Strict mode**: `disallow_untyped_defs = True` in mypy.ini
- Use `typing` module for generic types
- Use `Box` type for configuration objects

### Naming Conventions
- **Variables and functions**: `snake_case`
- **Classes**: `PascalCase`
- **Constants**: `UPPER_SNAKE_CASE`
- **Private members**: Prefix with underscore (`_`)

### Error Handling
- Use custom exception classes from `netsim.utils.log`:
  - `FatalError` for unrecoverable errors
  - `IncorrectAttr`, `IncorrectType`, `IncorrectValue` for validation errors
  - `MissingValue` for required but missing data
- Use `log.fatal()`, `log.error()`, `log.warning()` for user-facing messages
- Never use `print()` in library code (allowed in CLI modules)

### File Structure Patterns
- **CLI modules**: `netsim/cli/` - can use print statements
- **Device modules**: `netsim/devices/` - device-specific implementations
- **Extra modules**: `netsim/extra/` - optional plugins
- **Output modules**: `netsim/outputs/` - data export formats
- **Augment modules**: `netsim/augment/` - topology transformation

### Using Box objects

* The topology data structure is a Box object with `default_box=True` and `box_dots=True`
* In most cases, the Box object is converted into a dictionary before being used in a Jinja2 template

With the Box settings used in the topology data structure:

* The interim dictionaries are created automatically: `a.b.c=1` works even when `a.b` does not exist yet.
* The dotted paths can be used in indices (for example, `a['b.c'] = 1`) and in **in** tests (for example `'b.c' in a`)

### Using Jinja2 templates

* The Jinja2 environment uses a custom `undefined` method that can handle dictionary hierarchy. For example, `a.b.c is defined` returns False instead of crashing even when `a.b` does not exist. There is no need for an extra `a.b is defined` guard.
* Use `for ... if ...` loops whenever possible instead of separate `for` followed by `if`/`endif` block.
* Prefer `for key,value in some.dict|default({})|dictsort` over `if some.dict is defined` followed by the `for` loop.
* When in doubt, check the device configuration developer documentation. If that feels off, check the module topology transformation code.

### Testing Guidelines
- Test files in `tests/` directory
- Use `pytest` framework
- Integration tests in `tests/integration/`
- Validation tests in `tests/validation/`
- Coverage tests in `tests/coverage/`
- Error case tests in `tests/errors/`

### Configuration and Data
- Use `Box` objects for hierarchical configuration
- YAML files for configuration and topology definitions
- Jinja2 templates for configuration generation
- Global settings in `netsim/defaults/`

### Documentation
- Docstrings follow Google style (not strictly enforced but preferred)
- CLI help in `netsim/cli/help.py`
- User documentation in `docs/` directory

## Development Philosophy

From `.github/copilot-instructions.md`:
- **Think Different**: Question assumptions, seek elegant solutions
- **Obsess Over Details**: Understand existing patterns and codebase philosophy
- **Plan Like Da Vinci**: Document architecture before implementation
- **Craft, Don't Code**: Write elegant, self-documenting code
- **Iterate Relentlessly**: Test, refine, and improve continuously
- **Simplify Ruthlessly**: Remove complexity without losing power

## CRUCIAL: NO NITPICKING!!!

When you don't have to change the code for other reasons:

- DO NOT change single/double quotes
- DO NOT insert whitespaces
- DO NOT reformat code that would otherwise not be changed
- Keep comments aligned

## Key Dependencies
- **Jinja2**: Template rendering (>=3.1.4)
- **PyYAML**: YAML parsing (>=5.0.0)
- **netaddr**: Network address manipulation (>=0.8.0)
- **python-box**: Dictionary-like objects (>=7.2.0)
- **rich**: Terminal formatting
- **requests**: HTTP client

## Platform Requirements
- **Python**: 3.8+ (due to subprocess.capture_output and typing.Final)
- **OS**: Linux, macOS
- **Package managers**: pip, setuptools

## Quality Gates
- All code must pass `mypy` type checking
- All code must pass `ruff` linting and formatting
- All YAML must pass `yamllint`
- Tests must pass before merging
- No unused imports or variables (ruff enforces)

## Documentation

### Writing Configuration Template Development Documentation

* The documentation files must be in `docs/dev/config`
* The new files have to be included in ToC in `docs/dev/config/index.md`
* The *configuration template developer* documentation is not the user guide. The data structures described must match the output of the transformation process, not the input attribute schema, and there are significant differences between the two.
* There is no need to include supported platforms or more than three sample templates.
* The documentation must describe all relevant **node** attributes, followed by all relevant **interface** attributes. When needed, add VLAN- or VRF attributes.
* Do not explain the lab topology attributes; they have their own documentation.
* Find the relevant tests in the `tests/integration` directory tree and mention them
* Do not use `jinja2` syntax highlighter; it does not work.
* Mention where the configuration templates should be stored, and how the platform name is calculated (based on `netlab_device_type` or `ansible_network_os` variable)
