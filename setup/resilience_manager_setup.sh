#!/bin/bash

if [[ -z $(lsmod | grep "^hydra") ]]; then
  echo 'load hydra kernel module'
  modprobe hydra 
fi

if [[ -z $(mount | grep "configfs" | grep 'sys/kernel/config') ]]; then
  echo 'mount configfs'
  mount -t configfs none /sys/kernel/config
fi

if [[ $(nbdxadm -o show_host -i 0 | grep 'not configured') ]]; then
  echo 'configure host 0'
  nbdxadm -o create_host -i 0 -p $PWD/portal.list #portal.list
fi
if [[ $(nbdxadm -o show_device -i 0 -d 0 | grep 'not configured') ]]; then
  echo 'configure device 0'
  nbdxadm -o create_device -i 0 -d 0
fi

ls /dev/hydra0

if [[ -z $(swapon -s | grep '/dev/hydra0') ]]; then
  echo 'make swap device /dev/hydra0'
  mkswap /dev/hydra0
  swapon /dev/hydra0
fi
