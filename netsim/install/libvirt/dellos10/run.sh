#!/usr/bin/env python3
#
import sys
import os
import netsim.utils.strings as strings
import netsim.cli.external_commands as _xt
import netsim.cli.libvirt_actions.package as _pkg
import netsim.utils.files as _files
import netsim.utils.log as log

def find_file(glob: str) -> str:
  flist = _files.get_globbed_files('.',glob)
  if not flist:
    log.fatal(f'Cannot find {glob} in current directory','dellos10')

  if len(flist) > 1:
    log.fatal(
      f'More than one file matches the {glob} pattern. You must have a single OS10 version in current directory',
      module='dellos10')
    
  return flist[0]

def main() -> None:
  workdir = os.environ["NETLAB_PACKAGE_WORKDIR"]
  strings.print_colored_text('[CONVERT] ','green',None)
  print("Converting OS10 installer disk to qcow2 and copying it to build directory")
  inst_disk = find_file('OS10-Installer-*.vmdk')
  _pkg.abort_on_failure(f"qemu-img convert -f vmdk -O qcow2 {inst_disk} {workdir}/hdb_OS10-installer.qcow2")

  strings.print_colored_text('[INFO]    ','bright_cyan',None)
  print("Assuming S5224F as the hardware platform")
  hw_disk = find_file('OS10-platform*S5224F*vmdk')

  strings.print_colored_text('[CONVERT] ','green',None)
  print("Converting OS10 platform disk to qcow2 and copying it to build directory")
  _pkg.abort_on_failure(f"qemu-img convert -f vmdk -O qcow2 {hw_disk} {workdir}/hdc_OS10-platform.qcow2")

  return

if __name__ == "__main__":
    main()
