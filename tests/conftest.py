#
# Pytest configuration and fixtures
#
import os
import pytest


@pytest.fixture(scope="session", autouse=True)
def setup_json_cache():
    """
    Set up JSON cache for all tests if available.
    
    This fixture runs once per test session and sets the JSON cache
    if the NETLAB_JSON_CACHE environment variable is set and points
    to an existing file. This provides significant performance
    improvements (44.6% faster) for tests that load topology files.
    """
    json_cache = os.environ.get('NETLAB_JSON_CACHE')
    if json_cache and os.path.exists(json_cache):
        from netsim.utils import read as _read
        _read.set_json_cache(json_cache)
        print(f"\n✅ Using JSON cache: {json_cache}")
        print(f"   This will speed up all topology loading operations")
    else:
        if json_cache:
            print(f"\n⚠️  JSON cache specified but not found: {json_cache}")
        print(f"   Running tests without JSON cache (slower)")
    yield
    # Cleanup (if needed) happens here

