#!/bin/bash

SCRIPT_DIR=$( cd -- "$( dirname -- "${BASH_SOURCE[0]}" )" &> /dev/null && pwd )

# Create libvirt networks required for VM
cat > /tmp/vptx_PFE_LINK.xml << EOF
<network>
  <name>vptx_PFE_LINK</name>
</network>
EOF

cat > /tmp/vptx_RPIO_LINK.xml << EOF
<network>
  <name>vptx_RPIO_LINK</name>
</network>
EOF

virsh net-define /tmp/vptx_PFE_LINK.xml 2>/dev/null || true
virsh net-define /tmp/vptx_RPIO_LINK.xml 2>/dev/null || true
virsh net-start vptx_PFE_LINK 2>/dev/null || true
virsh net-start vptx_RPIO_LINK 2>/dev/null || true

# Create initial bootstrap virtual disk
cd $SCRIPT_DIR
./make-config.sh juniper.conf /tmp/vptx.bootstrap.qcow2
