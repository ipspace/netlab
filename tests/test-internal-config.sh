export NETLAB_PROVIDER=clab
d_list=`netlab show devices --format yaml|yq -r '. | keys | .[]'`
t_pattern=integration/**/[0-9]*.yml
#t_pattern=integration/initial/03*.yml
d_list="nxos routeros7 dnsmasq asav"
for device in $d_list; do
  echo "Testing device: $device"
  for test in $t_pattern; do
    t_name=`echo $test | awk -F/ '{print $(NF-1) "/" $NF}'`
    rm -r *files *vars config* clab* Vagrantfile 2>/dev/null
    t_id="$t_name $device"
    grep "$t_id" internal-configs.txt >/dev/null
    if [ $? -ne 0 ]; then
      NETLAB_DEVICE=$device netlab create "$test" >/dev/null 2>/dev/null
      if [ $? -eq 0 ]; then
        echo "Checking $t_name"
        set -e
        netlab initial --generate compare -o config_internal >/dev/null
        netlab initial --generate ansible -o config_ansible >/dev/null
        diff -rubB config_internal config_ansible
        set +e
        echo "OK: $t_name $device" >>internal-configs.txt
      else
        echo "Skipping $t_name"
        echo "SKIP: $t_name $device" >>internal-configs.txt
      fi
    fi
  done
done
