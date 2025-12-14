# Router ID Inconsistency Test Cases

This directory contains test cases to verify the router ID handling inconsistencies documented in `docs/router_id_inconsistencies.md`.

## Test Topologies

### test-bgp-vrf-router-id.yml
Tests BGP VRF router_id handling with:
- Global `bgp.router_id` set
- VRF-specific `vdata.bgp.router_id` set
- VRF without router_id (should fall back to global)

**Devices tested:**
- routeros7 (problematic)
- iosxr (problematic)
- nxos (problematic)
- junos (problematic)

### test-ospf-vrf-router-id.yml
Tests OSPF VRF router_id handling with:
- Global `ospf.router_id` set
- VRF-specific `vdata.ospf.router_id` set
- VRF without router_id (should fall back to global)

**Devices tested:**
- nxos (problematic)
- junos (problematic)
- vyos (correct but verbose)

### test-router-id-scenarios.yml
Comprehensive test covering all problematic devices and scenarios.

## Running the Tests

### Quick Start

```bash
cd tests/router_id_inconsistencies

# Generate all configs
./verify_router_id.sh

# Verify the generated configs
./verify_router_id.py
```

### Manual Steps

#### Generate Configurations

```bash
# Generate configs for BGP VRF test
cd tests/router_id_inconsistencies
netlab create -o none test-bgp-vrf-router-id.yml
netlab initial -o configs/test-bgp-vrf-router-id -i -m bgp test-bgp-vrf-router-id.yml

# Generate configs for OSPF VRF test
netlab create -o none test-ospf-vrf-router-id.yml
netlab initial -o configs/test-ospf-vrf-router-id -i -m ospf test-ospf-vrf-router-id.yml

# Generate configs for comprehensive test
netlab create -o none test-router-id-scenarios.yml
netlab initial -o configs/test-router-id-scenarios -i -m bgp,ospf test-router-id-scenarios.yml
```

#### Verify Configurations

```bash
# Run the Python verification script
./verify_router_id.py
```

### Automated Test Scripts

#### Bash Script (Generates Configs)

```bash
./verify_router_id.sh
```

This script will:
1. Generate configurations for all test topologies
2. Create output in `configs/` directory
3. Provide summary of what to check

#### Python Script (Verifies Configs)

```bash
# First generate configs
netlab create -o none test-bgp-vrf-router-id.yml
netlab initial -o configs/test-bgp-vrf-router-id -i -m bgp test-bgp-vrf-router-id.yml

# Then verify
./verify_router_id.py
```

The Python script will:
1. Check all generated config files
2. Verify router_id values match expectations
3. Report which tests pass/fail
4. Highlight inconsistencies

## Expected Issues to Verify

### BGP VRF Templates

1. **routeros7.bgp.j2**: Should use `vdata.bgp.router_id|default(bgp.router_id)` but currently uses `bgp.router_id` directly
   - Check: `configs/bgp-vrf/bgp_ros7.cfg` or VRF-specific config
   - Expected: VRF `vrf_with_rid` should use `100.100.100.100`, not `1.1.1.1`

2. **iosxr.bgp.j2**: Should fall back to `bgp.router_id` but currently only checks `vdata.bgp.router_id`
   - Check: `configs/bgp-vrf/bgp_iosxr.cfg` or VRF-specific config
   - Expected: VRF `vrf_no_rid` should use `2.2.2.2` (global), but may be missing

3. **nxos.bgp.j2**: Should use `vdata.bgp.router_id|default(bgp.router_id)` but currently uses `bgp.router_id` directly
   - Check: `configs/bgp-vrf/bgp_nxos.cfg` or VRF-specific config
   - Expected: VRF `vrf_with_rid` should use `100.100.100.100`, not `3.3.3.3`

4. **junos.bgp.j2**: Should work when only `vdata.bgp.router_id` is set, but outer check prevents it
   - Check: `configs/bgp-vrf/bgp_junos.cfg` or VRF-specific config
   - Expected: VRF `vrf_with_rid` should use `100.100.100.100`

### OSPF VRF Templates

1. **nxos.ospfv2-vrf.j2**: Should fall back to `ospf.router_id` but currently only checks `vdata.ospf.router_id`
   - Check: `configs/ospf-vrf/ospf_nxos.cfg` or VRF-specific config
   - Expected: VRF `vrf_no_rid` should use `10.10.10.10` (global), but may be missing

2. **junos.j2 (OSPF)**: Should fall back to `ospf.router_id` but currently only checks `vdata.ospf.router_id`
   - Check: `configs/ospf-vrf/ospf_junos.cfg` or VRF-specific config
   - Expected: VRF `vrf_no_rid` should use `20.20.20.20` (global), but may be missing

3. **vyos.ospfv2-vrf.j2** and **vyos.ospfv3-vrf.j2**: Should be correct (verbose but functional)
   - Check: `configs/ospf-vrf/ospf_vyos.cfg` or VRF-specific config
   - Expected: Should correctly use VRF-specific or fall back to global

## Manual Verification

After generating configurations, manually check:

1. **VRF with VRF-specific router_id**: Should use the VRF-specific value
2. **VRF without router_id**: Should fall back to global router_id
3. **VRF with only VRF-specific router_id (no global)**: Should still work (especially for junos.bgp.j2)

## Example Verification Commands

```bash
# Check routeros7 BGP VRF config
grep -A 5 "vrf.*vrf_with_rid\|vrf.*vrf_no_rid" configs/bgp-vrf/bgp_ros7.cfg | grep router-id

# Check iosxr BGP VRF config
grep -A 5 "vrf.*vrf_with_rid\|vrf.*vrf_no_rid" configs/bgp-vrf/bgp_iosxr.cfg | grep router-id

# Check nxos BGP VRF config
grep -A 5 "vrf.*vrf_with_rid\|vrf.*vrf_no_rid" configs/bgp-vrf/bgp_nxos.cfg | grep router-id

# Check junos BGP VRF config
grep -A 5 "vrf.*vrf_with_rid\|vrf.*vrf_no_rid" configs/bgp-vrf/bgp_junos.cfg | grep router-id

# Check nxos OSPF VRF config
grep -A 5 "vrf.*vrf_with_rid\|vrf.*vrf_no_rid" configs/ospf-vrf/ospf_nxos.cfg | grep router-id

# Check junos OSPF VRF config
grep -A 5 "vrf.*vrf_with_rid\|vrf.*vrf_no_rid" configs/ospf-vrf/ospf_junos.cfg | grep router-id
```

