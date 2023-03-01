#!/usr/bin/env bash
set -euo pipefail

NON_ROOT_USER=${NON_ROOT_USER:-ubuntu}

apt-get update
apt-get upgrade -y
apt-get install -y python3 python3-pip python3-venv curl

# Modify this list if there are build systems you don't want
apt-get install -y maven gradle golang nodejs rustc cargo cargo-lock

# Add the JDKs you'll need
apt-get install -y openjdk-19-jdk

# install -- replace PACKAGE_URL with your .tar.gz release URL
su ubuntu -c "cd \$HOME; python3 -m venv endor-venv; endor-venv/bin/pip3 install -e 'git+https://github.com/endorlabs/cloud-scanworker.git#egg=endor_scanworker&subdirectory=scanworker'"

# run -- add any scanworker options required to the end of the line
su ubuntu -c 'endor-venv/bin/endor-scanworker'
