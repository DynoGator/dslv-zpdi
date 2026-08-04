#!/bin/bash
# Draft restore script
sudo dpkg --set-selections < package_selections.txt
sudo apt-get dselect-upgrade -y
echo "Manual configurations from 'etc' and 'home_configs' need to be copied carefully!"
