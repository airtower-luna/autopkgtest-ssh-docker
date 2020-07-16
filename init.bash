#!/bin/bash
set -e
mkdir -p /run/sshd/
# autopkgtest needs current archive data to install dependencies
apt-get update
exec /usr/bin/systemctl
