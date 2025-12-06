(profile)=
# Profiling Lab Creation Performance

The **netlab create** command supports performance profiling to help identify bottlenecks and optimize lab creation time.

## Overview

When creating complex labs, **netlab create** performs many operations:
* Reading and parsing YAML files (topology, defaults, includes)
* Data transformation and augmentation
* Module processing
* Output file generation

Profiling helps identify where most time is spent, enabling targeted optimizations.

```{tip}
**Performance Analysis**: Profiling can reveal that 80-90% of execution time is spent in specific operations (like YAML parsing), helping prioritize optimization efforts.
```

## How It Works

The profiling feature uses Python's `cProfile` module to:
1. **Track execution**: Monitor all function calls during lab creation
2. **Measure time**: Record cumulative and total time spent in each function
3. **Generate reports**: Create detailed profiling reports showing where time is spent

## Usage

### Enabling Profiling

Use the `--profile` flag with **netlab create**:

```text
usage: netlab create [--profile [PROFILE_FILE]] [other options] [topology]

optional arguments:
  --profile [PROFILE_FILE]
                        Enable profiling and save results to file
                        (default: netlab.profile)
```

### Basic Usage

```bash
# Profile lab creation with default output file
netlab create --profile topology.yml

# Profile with custom output file
netlab create --profile my-profile.profile topology.yml
```

### Example Output

When profiling is enabled, you'll see:

```
[INFO] Profiling enabled, results will be saved to netlab.profile

Profiling data saved to netlab.profile

================================================================================
PROFILING SUMMARY - Top functions by cumulative time
================================================================================
         5848073 function calls (5811657 primitive calls) in 4.006 seconds

   Ordered by: cumulative time
   List reduced from 1306 to 30 due to restriction <30>

   ncalls  tottime  percall  cumtime  percall filename:lineno(function)
        1    0.000    0.000    3.535    3.535 netsim/cli/__init__.py:201(load_topology)
        1    0.002    0.002    3.535    3.535 netsim/utils/read.py:242(load)
     82/3    0.122    0.001    3.445    1.148 netsim/utils/read.py:97(read_yaml)
   ...
```

## Understanding Profiling Results

### Key Metrics

The profiling output shows several important metrics:

* **ncalls**: Number of times a function was called
* **tottime**: Total time spent in the function (excluding sub-functions)
* **cumtime**: Cumulative time (including sub-functions)
* **percall**: Average time per call

### Common Bottlenecks

Typical bottlenecks identified by profiling:

1. **YAML Parsing** (80-90% of time)
   - `read_yaml()` function calls
   - `ruamel.yaml` library operations
   - File I/O operations

2. **Topology Transformation** (5-15% of time)
   - Data augmentation
   - Module processing
   - Validation

3. **Output Generation** (1-5% of time)
   - Template rendering
   - File writing

## Analyzing Profile Data

### Using pstats

The generated profile file can be analyzed interactively:

```bash
python3 -m pstats netlab.profile
```

Within the pstats interface:
```
% sort cumulative
% stats 20
% stats read_yaml
```

### Generating Reports

Create text reports from profile data:

```bash
python3 -m pstats netlab.profile > profile_report.txt
```

Or use Python to generate custom reports:

```python
import pstats
stats = pstats.Stats('netlab.profile')
stats.sort_stats('cumulative')
stats.print_stats(30)  # Top 30 functions
```

## Best Practices

### When to Use Profiling

* **Performance Issues**: When lab creation is slower than expected
* **Optimization**: Before optimizing code to identify bottlenecks
* **Comparison**: To compare performance before/after changes
* **Debugging**: To understand execution flow and timing

### Profiling Workflow

1. **Baseline**: Profile the current implementation
   ```bash
   netlab create --profile baseline.profile topology.yml
   ```

2. **Optimize**: Make code changes based on profiling results

3. **Compare**: Profile again and compare results
   ```bash
   netlab create --profile optimized.profile topology.yml
   ```

4. **Analyze**: Use pstats or custom scripts to compare profiles

### Tips

* **Focus on cumulative time**: Functions with high cumulative time are good optimization targets
* **Look for hot paths**: Functions called many times (high ncalls) with moderate percall time
* **Check I/O operations**: File reads/writes are often bottlenecks
* **Compare before/after**: Use profiling to measure optimization impact

## Performance Optimization Examples

### Example: YAML Parsing Optimization

Profiling revealed that 88% of time was spent in YAML parsing:

```
load_topology: 3.535s (88% of total)
  read_yaml: 3.445s
    ruamel.yaml operations: 3.3s
```

This led to optimizations like:
* YAML file caching
* Reducing redundant file reads
* Optimizing include processing

### Example: Transformation Optimization

Profiling showed transformation taking significant time:

```
transform: 0.471s (12% of total)
  transform_setup: 0.232s
  transform_data: 0.180s
```

This helped identify which transformation steps were slowest.

## Limitations

* **Overhead**: Profiling adds some overhead (typically 5-10%)
* **File size**: Profile files can be large (several MB for complex labs)
* **Analysis time**: Analyzing large profiles can take time

## Related Commands

* **[netlab create](../netlab/create.md)**: Create lab configuration files (supports `--profile` flag)

## See Also

* [Python cProfile Documentation](https://docs.python.org/3/library/profile.html): Official profiling documentation

