#
# Create Vagrantfile from collected topology data
#

import common
import os

def get_template_path(topology,path):
  return path + '/templates/provider/' + topology['provider']

def dump(topology,path):
  template_path = get_template_path(topology,path)
  print("\nVagrantfile using templates from %s" % os.path.relpath(template_path))
  print("======================================================")
  print(common.template('Vagrantfile.j2',topology,template_path))

def create(topology,fname,path):
  with open(fname,"w") as output:
    output.write(common.template('Vagrantfile.j2',topology,get_template_path(topology,path)))
    output.close()
    print("Created Vagrantfile: %s" % fname)
