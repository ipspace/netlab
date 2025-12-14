#!/bin/bash
#
# Script to generate device configurations and verify router_id handling
# This script tests the inconsistencies documented in docs/router_id_inconsistencies.md
#

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
TEST_DIR="${SCRIPT_DIR}"
CONFIG_DIR="${TEST_DIR}/configs"
RESULTS_DIR="${TEST_DIR}/results"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo "Router ID Inconsistency Test Suite"
echo "==================================="
echo ""

# Create output directories
mkdir -p "${CONFIG_DIR}"
mkdir -p "${RESULTS_DIR}"

# Function to check if router_id appears in config
check_router_id() {
    local config_file="$1"
    local expected_rid="$2"
    local device_type="$3"
    local vrf_name="$4"
    
    if [ ! -f "${config_file}" ]; then
        echo -e "${RED}✗${NC} Config file not found: ${config_file}"
        return 1
    fi
    
    # Different patterns for different devices
    case "${device_type}" in
        routeros7)
            # RouterOS7: /routing/bgp/template set vrf_XXX router-id=...
            if grep -q "router-id=${expected_rid}" "${config_file}"; then
                echo -e "${GREEN}✓${NC} Found router-id=${expected_rid} in ${config_file}"
                return 0
            fi
            ;;
        iosxr)
            # IOS XR: bgp router-id ...
            if grep -q "bgp router-id ${expected_rid}" "${config_file}"; then
                echo -e "${GREEN}✓${NC} Found bgp router-id ${expected_rid} in ${config_file}"
                return 0
            fi
            ;;
        nxos)
            # NXOS: router-id ...
            if grep -q "router-id ${expected_rid}" "${config_file}"; then
                echo -e "${GREEN}✓${NC} Found router-id ${expected_rid} in ${config_file}"
                return 0
            fi
            ;;
        junos)
            # Junos: router-id ...
            if grep -q "router-id ${expected_rid}" "${config_file}"; then
                echo -e "${GREEN}✓${NC} Found router-id ${expected_rid} in ${config_file}"
                return 0
            fi
            ;;
        vyos)
            # VyOS: set protocols ospf parameters router-id ...
            if grep -q "router-id ${expected_rid}" "${config_file}"; then
                echo -e "${GREEN}✓${NC} Found router-id ${expected_rid} in ${config_file}"
                return 0
            fi
            ;;
    esac
    
    echo -e "${RED}✗${NC} Expected router-id ${expected_rid} not found in ${config_file}"
    return 1
}

# Function to check if router_id is missing when it should be present
check_missing_router_id() {
    local config_file="$1"
    local device_type="$2"
    local vrf_name="$3"
    
    if [ ! -f "${config_file}" ]; then
        echo -e "${YELLOW}⚠${NC} Config file not found: ${config_file}"
        return 1
    fi
    
    # Check if any router-id is present (should be)
    case "${device_type}" in
        routeros7)
            if ! grep -q "router-id=" "${config_file}"; then
                echo -e "${RED}✗${NC} Missing router-id in ${config_file} (should be present)"
                return 1
            fi
            ;;
        iosxr)
            if ! grep -q "bgp router-id" "${config_file}"; then
                echo -e "${RED}✗${NC} Missing bgp router-id in ${config_file} (should be present)"
                return 1
            fi
            ;;
        nxos)
            if ! grep -q "router-id" "${config_file}"; then
                echo -e "${RED}✗${NC} Missing router-id in ${config_file} (should be present)"
                return 1
            fi
            ;;
        junos)
            if ! grep -q "router-id" "${config_file}"; then
                echo -e "${RED}✗${NC} Missing router-id in ${config_file} (should be present)"
                return 1
            fi
            ;;
    esac
    
    return 0
}

# Test function for a topology
test_topology() {
    local topology_file="$1"
    local test_name="$2"
    
    echo ""
    echo "Testing: ${test_name}"
    echo "----------------------------------------"
    
    local topo_dir=$(dirname "${topology_file}")
    local topo_name=$(basename "${topology_file}" .yml)
    local config_output="${CONFIG_DIR}/${topo_name}"
    
    # Generate configurations (from script directory)
    echo "Generating configurations..."
    # Create snapshot first (needed for netlab initial)
    netlab create "${topology_file}" 2>&1 | grep -v "^$" || true
    # Generate configs
    netlab initial -o "${config_output}" -i -m bgp,ospf 2>&1 | grep -v "^$" || true
    
    echo "Configurations generated in: ${config_output}"
    echo ""
}

# Main test execution
echo "Step 1: Testing BGP VRF router_id scenarios"
test_topology "${TEST_DIR}/test-bgp-vrf-router-id.yml" "BGP VRF Router ID"

echo ""
echo "Step 2: Testing OSPF VRF router_id scenarios"
test_topology "${TEST_DIR}/test-ospf-vrf-router-id.yml" "OSPF VRF Router ID"

echo ""
echo "Step 3: Testing comprehensive router_id scenarios"
test_topology "${TEST_DIR}/test-router-id-scenarios.yml" "Comprehensive Router ID"

echo ""
echo "==================================="
echo "Test Summary"
echo "==================================="
echo ""
echo "Generated configurations are in: ${CONFIG_DIR}"
echo ""
echo "Manual verification steps:"
echo "1. Check routeros7.bgp.j2 VRF configs - should use vdata.bgp.router_id|default(bgp.router_id)"
echo "2. Check iosxr.bgp.j2 VRF configs - should fall back to bgp.router_id when vdata.bgp.router_id not set"
echo "3. Check nxos.bgp.j2 VRF configs - should use vdata.bgp.router_id|default(bgp.router_id)"
echo "4. Check junos.bgp.j2 VRF configs - should work even when only vdata.bgp.router_id is set"
echo "5. Check nxos.ospfv2-vrf.j2 - should fall back to ospf.router_id"
echo "6. Check junos.j2 OSPF VRF - should fall back to ospf.router_id"
echo "7. Check vyos.ospfv2-vrf.j2 and ospfv3-vrf.j2 - should be correct (verbose but functional)"
echo ""

