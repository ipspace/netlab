setup() {
  load 'support/common'
  _common
  create-topology --topology tests/hosts/input/clab-oci.yml \
        -p clab-oci.yml \
        --inventory \
        --config
}

teardown() {
  rm -rf hosts.yml
}

@test "ContainerLab hosts file is generated" {
  run diff hosts.yml tests/hosts/expected/clab-oci.yml
  assert_success
}
