#!/bin/bash
rm -rf downstream
mkdir downstream
for play in $(ls -1 playbooks/*.yml)
do
  ansible-playbook "${play}" &
done
