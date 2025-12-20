#!/bin/bash
netlab initial --generate compare -o config_internal
diff -rubB config_internal config_ansible
