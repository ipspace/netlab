setup() {
  load 'support/common'
  _common

  TOPO=$TOOLS/tests/containerlab/fixtures/frr:latest.yml

  pushd $TOOLS
    ./create-topology --topology $TOPO \
                      -p test-clab.yml \
                      --inventory \
                      --config \
                      --log
  popd
}

teardown() {
  pushd $TOOLS
    # Upon containerlab support for Podman we can remove sudo
    sudo /usr/bin/containerlab destroy --topo test-clab.yml

    # A side effect of sudo requirement of Docker
    sudo rm -rf clab-test-latest/ansible-inventory.yml

    rm -fr ansible.cfg clab-test-latest hosts.yml host_vars group_vars test-clab.yml
  popd
}

@test "FRR latest container runs" {
  # Upon containerlab support for Podman we can remove sudo
  # Or require rootless configuration for Docker (PITA).
  run sudo /usr/bin/containerlab deploy --runtime docker --topo test-clab.yml
  assert_output --regexp 'clab-test-latest-e1 (.*) running'
  assert_output --regexp 'clab-test-latest-e2 (.*) running'
  assert_output --regexp 'clab-test-latest-c1 (.*) running'
  assert_output --regexp 'clab-test-latest-c2 (.*) running'
}
