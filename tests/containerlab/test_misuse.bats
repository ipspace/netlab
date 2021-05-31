setup() {
  load 'support/common'
  _common
}

@test "Show error message on use without arguments" {
  run create-topology
  assert_output --partial 'Cannot read topology file'
}

# @test "Show help instructions on use without arguments" {
#   skip 'Not implemented. See issue #28'
#   run create-topology
#   assert_output --partial 'usage: create-topology'
# }