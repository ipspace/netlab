setup() {
  load 'support/common'
  _common

  TOPO=$TOOLS/tests/containerlab/fixtures/frr.yml

  pushd $TOOLS
    ./create-topology --topology $TOPO \
                      -p test-clab.yml \
                      --inventory \
                      --config \
                      --log
    # Upon containerlab support for Podman we can remove sudo
    # Or require rootless configuration for Docker (PITA).
    sudo /usr/bin/containerlab deploy --runtime docker --topo test-clab.yml
  popd
}

teardown() {
  pushd $TOOLS
    # Upon containerlab support for Podman we can remove sudo
    sudo /usr/bin/containerlab destroy --topo test-clab.yml

    # A side effect of sudo requirement of Docker
    sudo rm -rf clab-test-connect/ansible-inventory.yml

    rm -fr ansible.cfg clab-test-connect frr.yml hosts.yml host_vars group_vars test-clab.yml
  popd
}

@test "Connect passes user command and arguments" {
  run sudo ./connect.sh e2 ip a
  assert_output --partial 'inet 172.20.20.7/24 brd 172.20.20.255 scope global eth0'
}
