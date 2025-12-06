#
# Profiling utilities for netlab
#
import cProfile
import pstats
from contextlib import contextmanager
from typing import Generator, Optional

_profiler: Optional[cProfile.Profile] = None
_profile_output: Optional[str] = None

def start_profiling(output_file: str = "netlab.profile") -> None:
    """Start profiling and set output file"""
    global _profiler, _profile_output
    _profiler = cProfile.Profile()
    _profile_output = output_file
    _profiler.enable()

def stop_profiling() -> None:
    """Stop profiling and save results"""
    global _profiler, _profile_output
    if _profiler is None:
        return

    _profiler.disable()

    if _profile_output:
        _profiler.dump_stats(_profile_output)
        print(f"\nProfiling data saved to {_profile_output}")
        print_summary(_profile_output)

def print_summary(profile_file: str, lines: int = 30) -> None:
    """Print a summary of profiling results"""
    stats = pstats.Stats(profile_file)

    print("\n" + "="*80)
    print("PROFILING SUMMARY - Top functions by cumulative time")
    print("="*80)
    stats.sort_stats('cumulative')
    stats.print_stats(lines)

    print("\n" + "="*80)
    print("PROFILING SUMMARY - Top functions by total time")
    print("="*80)
    stats.sort_stats('tottime')
    stats.print_stats(lines)

    print("\n" + "="*80)
    print("PROFILING SUMMARY - Top functions by number of calls")
    print("="*80)
    stats.sort_stats('ncalls')
    stats.print_stats(lines)

@contextmanager
def profile_context(output_file: str = "netlab.profile") -> Generator[None, None, None]:
    """Context manager for profiling a code block"""
    start_profiling(output_file)
    try:
        yield
    finally:
        stop_profiling()

def is_profiling() -> bool:
    """Check if profiling is currently active"""
    # cProfile.Profile doesn't have is_running(), so we check if profiler exists
    # and assume it's running if it's been created (since we enable it immediately)
    return _profiler is not None

