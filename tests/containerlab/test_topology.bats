setup() {
  load 'support/common'
  _common
  create-topology --topology tests/topology/input/clab-oci.yml \
        -p clab-oci.yml \
        --inventory \
        --config
}

teardown() {
  rm -rf clab-oci.yml
}

@test "ContainerLab topology file is generated" {
  run diff clab-oci.yml tests/topology/expected/clab-oci.yml
  assert_success
}
