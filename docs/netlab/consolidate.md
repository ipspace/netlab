(netlab-consolidate)=
# Consolidate YAML Files into JSON Cache

The **netlab consolidate** command collects all YAML files (topology, defaults, modules, devices, providers) that would be loaded during a `netlab create` operation and consolidates them into a single JSON file. This JSON cache can then be used with the `--json-cache` flag to significantly speed up subsequent `netlab create` operations.

## Why Use Consolidation?

When `netlab create` runs, it reads many YAML files:
- Topology file and any included files
- Default settings files (project, user, system)
- Module definitions
- Device configurations
- Provider configurations

Each file requires:
- File system I/O operations
- YAML parsing (slower than JSON parsing)
- Path resolution and file lookups

By consolidating these files into a single JSON cache, you can:
- **Reduce I/O operations**: One file read instead of 80+ separate files
- **Faster parsing**: JSON parsing is significantly faster than YAML parsing
- **Eliminate file lookups**: All data is pre-resolved and ready to use
- **Improve CI/CD performance**: Pre-consolidate once, use cache for all tests

## Performance Benefits

Based on EVPN integration test results:
- **44.6% faster** execution time (1.81x speedup)
- **19.59 seconds saved** per full test suite run
- Consistent improvement across all topology files

For example, a test that takes 2.44 seconds without cache takes only 1.35 seconds with cache.

## Usage

### Consolidate a Specific Topology

To consolidate all YAML files for a specific topology:

```bash
netlab consolidate topology.yml -o cache.json
```

This will:
1. Load the topology file and all its dependencies
2. Track all YAML files that get read (defaults, modules, devices, providers)
3. Consolidate them into a single JSON file
4. Validate the structure against a JSON schema (if `jsonschema` is installed)

### Consolidate All System Files

To consolidate all system/package YAML files without a topology (useful for CI/CD):

```bash
netlab consolidate -o system-cache.json
```

This consolidates:
- All system defaults files
- All module definitions
- All device configurations
- All provider configurations
- Package files

This is particularly useful for integration test suites where you want to cache all default files once and reuse them across multiple labs.

### Using the JSON Cache

After creating a consolidated JSON file, use it with `netlab create`:

```bash
netlab create --json-cache cache.json topology.yml
```

The `--json-cache` flag tells `netlab create` to:
1. Load the consolidated JSON file instead of reading individual YAML files
2. Use the pre-parsed content directly
3. Skip YAML parsing and file I/O operations

## Command Syntax

```text
usage: netlab consolidate [-h] [--log] [-q] [-v] [--defaults DEFAULTS]
                          [-d DEVICE] [-p PROVIDER] [-s SETTINGS]
                          [--plugin PLUGIN] [-o OUTPUT] [topology]

Consolidate all YAML files into a single JSON file for faster loading

positional arguments:
  topology              Topology file to consolidate (optional: if omitted,
                        consolidates all system/package YAML files)

optional arguments:
  -h, --help            show this help message and exit
  --log                 Enable basic logging
  -q, --quiet           Report only major errors
  -v, --verbose         Verbose logging
  --defaults DEFAULTS   Local topology defaults file
  -d DEVICE, --device DEVICE
                        Default device type
  -p PROVIDER, --provider PROVIDER
                        Override virtualization provider
  --plugin PLUGIN       Additional plugin(s)
  -s SETTINGS, --set SETTINGS
                        Additional parameters added to topology file
  -o OUTPUT, --output OUTPUT
                        Output JSON file (default: netlab.consolidated.json)
```

## JSON Cache Structure

The consolidated JSON file has the following structure:

```json
{
  "version": "1.0",
  "netlab_version": "25.12.02",
  "topology_file": "topology.yml",
  "files": {
    "/path/to/topology.yml": {
      "content": { ... },
      "source": "topology.yml",
      "package": false
    },
    "package:topology-defaults.yml": {
      "content": { ... },
      "source": "package:topology-defaults.yml",
      "package": true
    },
    ...
  },
  "file_count": 95
}
```

Each file entry contains:
- **content**: The parsed YAML content as a dictionary/object
- **source**: The original filename/path
- **package**: Whether this is a package file (starts with `package:`)

## Version Compatibility

The consolidated JSON cache includes the **netlab version** that created it. When loading a cache file, netlab checks if the cache version matches the current netlab version:

- **Version matches**: Cache is used normally
- **Version mismatch**: Cache is rejected with an error message, and you must regenerate it

This ensures that cache files are only used with compatible netlab versions, preventing issues from:
- Changes in YAML file structure between versions
- Modified default settings or module definitions
- Updated device or provider configurations

**Example error when versions don't match:**
```
ERROR: JSON cache cache.json was created with netlab version 25.12.01
ERROR: Current netlab version is 25.12.02
ERROR: Cache file is incompatible and must be regenerated
ERROR: Please run "netlab consolidate" again to create a new cache
```

## Schema Validation

The consolidated JSON cache is validated against a JSON schema to ensure data integrity. The schema validates:
- Overall structure (version, netlab_version, files, file_count)
- File entry structure (content, source, package)
- Content properties (nodes, links, modules, devices, providers, etc.)

Schema validation is **optional** and requires the `jsonschema` package. If `jsonschema` is not installed, consolidation will still work, but validation will be skipped.

To install schema validation support:

```bash
pip install jsonschema
```

## Use Cases

### Development Workflow

1. Consolidate once at the start of your session:
   ```bash
   netlab consolidate -o cache.json
   ```

2. Use the cache for all subsequent `netlab create` operations:
   ```bash
   netlab create --json-cache cache.json topology.yml
   ```

3. Re-consolidate if you modify defaults or system files

### CI/CD Pipelines

1. Pre-consolidate system files once:
   ```bash
   netlab consolidate -o system-cache.json
   ```

2. Use the cache for all integration tests:
   ```bash
   for topo in tests/integration/*/*.yml; do
     netlab create --json-cache system-cache.json "$topo"
   done
   ```

This provides significant time savings when running large test suites.

### Integration Testing

For integration test suites with many topology files:

1. Create a system cache once:
   ```bash
   netlab consolidate -o system-cache.json
   ```

2. Run all tests with the cache:
   ```bash
   netlab create --json-cache system-cache.json test-topology.yml
   ```

This can reduce test execution time by 40-50%.

## Limitations

- The JSON cache must be regenerated if:
  - **Netlab version changes** (automatic check - cache will be rejected)
  - System defaults files change
  - Module definitions change
  - Device or provider configurations change
  - The topology file or its includes change

- **Version compatibility**: The cache includes the netlab version that created it. If you upgrade netlab, the cache will be automatically rejected and you'll need to regenerate it.

- Schema validation requires the `jsonschema` package, but is optional.

## Examples

### Example 1: Consolidate and Use for Single Topology

```bash
# Consolidate topology and all dependencies
netlab consolidate my-topology.yml -o my-cache.json

# Use the cache for faster creation
netlab create --json-cache my-cache.json my-topology.yml
```

### Example 2: CI/CD Pipeline

```bash
# Pre-consolidate system files (run once)
netlab consolidate -o system-cache.json

# Use cache for all tests
for test in tests/integration/**/*.yml; do
  netlab create --json-cache system-cache.json "$test" -p clab -d frr
done
```

### Example 3: Development Iteration

```bash
# Start of session: consolidate system files
netlab consolidate -o dev-cache.json

# During development: use cache for quick iterations
netlab create --json-cache dev-cache.json topology.yml
netlab create --json-cache dev-cache.json topology.yml  # Much faster!
```

## Related Commands

- **[netlab create](netlab-create)**: Create lab configuration files (supports `--json-cache` flag)
- **[netlab defaults](netlab-defaults)**: Manage default settings files

