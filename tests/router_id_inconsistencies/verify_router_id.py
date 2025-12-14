#!/usr/bin/env python3
"""
Verify router_id handling in generated device configurations.

This script checks for the inconsistencies documented in docs/router_id_inconsistencies.md
"""

import re
import sys
from pathlib import Path
from typing import Optional, Tuple

# Color codes
RED = '\033[0;31m'
GREEN = '\033[0;32m'
YELLOW = '\033[1;33m'
BLUE = '\033[0;34m'
NC = '\033[0m'  # No Color

# Expected router_id patterns for different devices
ROUTER_ID_PATTERNS = {
    'routeros7': {
        'bgp': r'router-id=([0-9.]+)',
        'context': r'/routing/bgp/template set vrf_(\w+)',
    },
    'iosxr': {
        'bgp': r'bgp router-id ([0-9.]+)',
        'context': r'vrf (\w+)',
    },
    'nxos': {
        'bgp': r'router-id ([0-9.]+)',
        'context': r'vrf (\w+)',
    },
    'junos': {
        'bgp': r'router-id ([0-9.]+)',
        'context': r'(\w+) \{',
    },
    'vyos': {
        'ospf': r'router-id ([0-9.]+)',
        'context': r'vrf (\w+)',
    },
}

# Test expectations: (device, vrf_name, expected_router_id, protocol)
EXPECTATIONS = {
    'test-bgp-vrf-router-id.yml': [
        # VRF vrf1 has vdata.bgp.router_id = 10.10.10.10
        ('r1', 'vrf1', '10.10.10.10', 'bgp'),  # routeros7 - should use VRF-specific
        ('r2', 'vrf1', '10.10.10.10', 'bgp'),  # iosxr - should use VRF-specific
        ('r3', 'vrf1', '10.10.10.10', 'bgp'),  # nxos - should use VRF-specific
        ('r4', 'vrf1', '10.10.10.10', 'bgp'),  # routeros7 - should use VRF-specific
        ('r5', 'vrf1', '10.10.10.10', 'bgp'),  # junos - should use VRF-specific
        # VRF vrf2 has no router_id - should fall back to global
        ('r1', 'vrf2', '1.1.1.1', 'bgp'),  # routeros7 - should use global
        ('r2', 'vrf2', '2.2.2.2', 'bgp'),  # iosxr - should use global (may be missing - bug)
        ('r3', 'vrf2', '3.3.3.3', 'bgp'),  # nxos - should use global (may be missing - bug)
        ('r4', 'vrf2', '4.4.4.4', 'bgp'),  # routeros7 - should use global
        ('r5', 'vrf2', '5.5.5.5', 'bgp'),  # junos - should use global
    ],
    'test-ospf-vrf-router-id.yml': [
        # VRF vrf1 has vdata.ospf.router_id = 10.10.10.10
        ('r1', 'vrf1', '10.10.10.10', 'ospf'),  # nxos - should use VRF-specific
        ('r2', 'vrf1', '10.10.10.10', 'ospf'),  # junos - should use VRF-specific
        ('r3', 'vrf1', '10.10.10.10', 'ospf'),  # vyos - should use VRF-specific
        # VRF vrf2 has no router_id - should fall back to global
        ('r1', 'vrf2', '1.1.1.1', 'ospf'),  # nxos - should use global (may be missing - bug)
        ('r2', 'vrf2', '2.2.2.2', 'ospf'),  # junos - should use global (may be missing - bug)
        ('r3', 'vrf2', '3.3.3.3', 'ospf'),  # vyos - should use global
    ],
    'test-router-id-scenarios.yml': [
        # VRF vrf_with_rid has vdata.bgp.router_id = 100.100.100.100
        ('bgp_ros7', 'vrf_with_rid', '100.100.100.100', 'bgp'),
        ('bgp_iosxr', 'vrf_with_rid', '100.100.100.100', 'bgp'),
        ('bgp_nxos', 'vrf_with_rid', '100.100.100.100', 'bgp'),
        ('bgp_junos', 'vrf_with_rid', '100.100.100.100', 'bgp'),
        # VRF vrf_no_rid has no router_id - should fall back to global
        ('bgp_ros7', 'vrf_no_rid', '1.1.1.1', 'bgp'),
        ('bgp_iosxr', 'vrf_no_rid', '2.2.2.2', 'bgp'),
        ('bgp_nxos', 'vrf_no_rid', '3.3.3.3', 'bgp'),
        ('bgp_junos', 'vrf_no_rid', '4.4.4.4', 'bgp'),
        # OSPF VRF tests
        ('ospf_nxos', 'vrf_with_rid', '200.200.200.200', 'ospf'),
        ('ospf_junos', 'vrf_with_rid', '200.200.200.200', 'ospf'),
        ('ospf_vyos', 'vrf_with_rid', '200.200.200.200', 'ospf'),
        ('ospf_nxos', 'vrf_no_rid', '10.10.10.10', 'ospf'),
        ('ospf_junos', 'vrf_no_rid', '20.20.20.20', 'ospf'),
        ('ospf_vyos', 'vrf_no_rid', '30.30.30.30', 'ospf'),
    ],
}


def find_router_id_in_config(config_content: str, device_type: str, protocol: str, vrf_name: Optional[str] = None) -> Optional[str]:
    """Extract router_id from config content for a specific VRF."""
    patterns = ROUTER_ID_PATTERNS.get(device_type, {})
    pattern = patterns.get(protocol)
    
    if not pattern:
        return None
    
    # For VRF-specific configs, we need to find the router_id within the VRF context
    if vrf_name:
        context_pattern = patterns.get('context')
        if context_pattern:
            # Find all VRF sections
            vrf_sections = []
            lines = config_content.split('\n')
            in_vrf = False
            vrf_start = 0
            current_vrf = None
            
            for i, line in enumerate(lines):
                # Check for VRF context start
                context_match = re.search(context_pattern, line)
                if context_match:
                    if in_vrf and current_vrf:
                        vrf_sections.append((current_vrf, vrf_start, i))
                    current_vrf = context_match.group(1)
                    vrf_start = i
                    in_vrf = True
                    if current_vrf == vrf_name:
                        break
            
            # If we found the target VRF, search within its section
            if current_vrf == vrf_name:
                vrf_content = '\n'.join(lines[vrf_start:])
                # Find router_id within this VRF section
                match = re.search(pattern, vrf_content)
                if match:
                    return match.group(1)
    
    # Fallback: search entire config
    match = re.search(pattern, config_content)
    if match:
        return match.group(1)
    
    return None


def check_config_file(config_path: Path, device_name: str, device_type: str, 
                     vrf_name: str, expected_rid: str, protocol: str) -> Tuple[bool, str]:
    """Check if a config file has the expected router_id for a VRF."""
    if not config_path.exists():
        return False, f"Config file not found: {config_path}"
    
    try:
        content = config_path.read_text()
    except Exception as e:
        return False, f"Error reading config: {e}"
    
    found_rid = find_router_id_in_config(content, device_type, protocol, vrf_name)
    
    if found_rid is None:
        return False, f"No router_id found for VRF {vrf_name}"
    
    if found_rid == expected_rid:
        return True, f"Found expected router_id {found_rid} for VRF {vrf_name}"
    else:
        return False, f"Found router_id {found_rid}, expected {expected_rid} for VRF {vrf_name}"


def get_device_type_from_config(config_path: Path) -> Optional[str]:
    """Try to determine device type from config content."""
    if not config_path.exists():
        return None
    
    try:
        content = config_path.read_text()
    except Exception:
        return None
    
    # Simple heuristics based on config syntax
    if '/routing/bgp/template' in content:
        return 'routeros7'
    elif 'router bgp' in content and 'address-family vpn' in content:
        return 'iosxr'
    elif 'router bgp' in content and 'vrf' in content and 'router-id' in content:
        return 'nxos'
    elif 'routing-instances' in content:
        return 'junos'
    elif 'set protocols ospf' in content:
        return 'vyos'
    
    return None


def main():
    script_dir = Path(__file__).parent
    test_dir = script_dir
    config_dir = test_dir / 'configs'
    
    if not config_dir.exists():
        print(f"{RED}Error:{NC} Config directory not found: {config_dir}")
        print(f"Please run 'netlab initial -o configs' first to generate configurations.")
        sys.exit(1)
    
    print(f"{BLUE}Router ID Inconsistency Verification{NC}")
    print("=" * 50)
    print()
    
    total_tests = 0
    passed_tests = 0
    failed_tests = []
    
    # Device type mapping (from topology node names)
    device_type_map = {
        'r1': 'routeros7',  # From test-bgp-vrf-router-id.yml
        'r2': 'iosxr',
        'r3': 'nxos',
        'r4': 'routeros7',
        'r5': 'junos',
        'bgp_ros7': 'routeros7',
        'bgp_iosxr': 'iosxr',
        'bgp_nxos': 'nxos',
        'bgp_junos': 'vjunos-router',
        'ospf_nxos': 'nxos',
        'ospf_junos': 'vjunos-router',
        'ospf_vyos': 'vyos',
    }
    
    # Check each test topology
    for topology_file, expectations in EXPECTATIONS.items():
        topo_name = Path(topology_file).stem
        topo_config_dir = config_dir / topo_name
        
        if not topo_config_dir.exists():
            print(f"{YELLOW}Warning:{NC} Config directory not found: {topo_config_dir}")
            print(f"  Run: netlab initial -o configs/{topo_name} -i -m bgp,ospf {topology_file}")
            print()
            continue
        
        print(f"{BLUE}Testing: {topology_file}{NC}")
        print("-" * 50)
        
        for device_name, vrf_name, expected_rid, protocol in expectations:
            total_tests += 1
            
            device_type = device_type_map.get(device_name)
            if not device_type:
                # Try to infer from config file
                config_path = topo_config_dir / f"{device_name}.cfg"
                device_type = get_device_type_from_config(config_path)
            
            if not device_type:
                print(f"{YELLOW}⚠{NC}  {device_name}/{vrf_name}: Could not determine device type")
                failed_tests.append((device_name, vrf_name, "Unknown device type"))
                continue
            
            # Look for config file (could be .cfg or device-specific extension)
            config_path = topo_config_dir / f"{device_name}.cfg"
            if not config_path.exists():
                # Try alternative names
                alt_paths = [
                    topo_config_dir / f"{device_name}.{protocol}.cfg",
                    topo_config_dir / f"{device_name}.initial.cfg",
                ]
                for alt_path in alt_paths:
                    if alt_path.exists():
                        config_path = alt_path
                        break
            
            success, message = check_config_file(
                config_path, device_name, device_type, vrf_name, expected_rid, protocol
            )
            
            if success:
                print(f"{GREEN}✓{NC}  {device_name}/{vrf_name}: {message}")
                passed_tests += 1
            else:
                print(f"{RED}✗{NC}  {device_name}/{vrf_name}: {message}")
                failed_tests.append((device_name, vrf_name, message))
        
        print()
    
    # Summary
    print("=" * 50)
    print(f"{BLUE}Summary{NC}")
    print(f"Total tests: {total_tests}")
    print(f"{GREEN}Passed: {passed_tests}{NC}")
    print(f"{RED}Failed: {len(failed_tests)}{NC}")
    print()
    
    if failed_tests:
        print(f"{RED}Failed Tests:{NC}")
        for device, vrf, msg in failed_tests:
            print(f"  {device}/{vrf}: {msg}")
        print()
        print("These failures may indicate the router_id inconsistencies documented")
        print("in docs/router_id_inconsistencies.md")
        sys.exit(1)
    else:
        print(f"{GREEN}All tests passed!{NC}")
        sys.exit(0)


if __name__ == '__main__':
    main()

