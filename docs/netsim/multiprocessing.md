# Multiprocessing Configuration

netlab automatically uses multiprocessing for file generation when processing large topologies. You can configure the exact number of workers used to optimize performance for your specific hardware.

## Default Behavior

netlab tries to determines the optimal number of workers based on your system:

- **Small systems (≤4 cores)**: Uses all available CPU cores for maximum performance
- **Large systems (>4 cores)**: Uses 75% of available CPU cores to avoid overwhelming the system

This provides a good balance between performance and system stability across all system sizes.

## Configuration Options

You can override the default 75% by setting `max_workers` to an exact number in your topology file or defaults.

The setting is configured under `defaults.multiprocessing.max_workers` in your YAML files.

### In Topology File

```yaml
defaults:
  multiprocessing:
    max_workers: 16    # Use exactly 16 workers
```

### In User Defaults

Add to `~/.netlab.yml`:

```yaml
defaults:
  multiprocessing:
    max_workers: 20
```

### In Project Defaults

Create `defaults.yml` in your project directory:

```yaml
defaults:
  multiprocessing:
    max_workers: 12
```

## What Happens When No Configuration is Provided

If you don't specify any multiprocessing settings, netlab automatically chooses the best configuration:

**4-core VM (like yours):**
- System detects 4 cores
- Since 4 ≤ 4, uses all 4 cores
- Output: `4 workers (using all 4 available cores)`

**72-core server:**
- System detects 72 cores  
- Since 72 > 4, uses 75% of cores (54 workers)
- Output: `54 workers (auto-scaled to 75% of 72 available cores)`

**Custom configuration:**
- If you set `max_workers: 100`, it uses exactly 100
- Output: `100 workers (configured: 100, available cores: 72)`

## Examples
```yaml
defaults:
  multiprocessing:
    max_workers: 100    # Use 100 workers (can exceed CPU cores for I/O-bound tasks)
```

### Development VM (4 cores, 8GB RAM)
```yaml
defaults:
  multiprocessing:
    max_workers: 4     # Use all available cores
```

### Conservative Setting
```yaml
defaults:
  multiprocessing:
    max_workers: 8     # Conservative limit regardless of CPU count
```

## Performance Considerations

- **Too few workers**: Underutilizes your hardware
- **Too many workers**: Can cause resource contention and slower performance
- **Optimal range**: Usually 50-75% of available CPU cores

## Progress Tracking

netlab supports real-time progress tracking during file processing, but it comes with a **significant performance cost**.

### Performance Impact

- **Progress disabled (default)**: Maximum performance, no visual feedback
- **Progress enabled**: **half as fast** on large jobs and low end devices

### When to Enable Progress

**Enable progress for:**
- Development and testing
- When you need to monitor progress

**Disable progress for:**
- Production deployments
- Large labs (>100 nodes)
- Maximum performance requirements

### Configuration

**Enable progress in your topology:**
```yaml
defaults:
  multiprocessing:
    max_workers: 8
    show_progress: true    # Enable progress bar (slower)
```

**Disable progress (default, fastest):**
```yaml
defaults:
  multiprocessing:
    max_workers: 8
    show_progress: false   # Disable progress bar (fastest)
```

## Monitoring

When multiprocessing is used, netlab displays the worker configuration:

```
[WORKERS]    Using 16 workers (configured: 20, available cores: 20)
```