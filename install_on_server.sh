#!/bin/bash
apt-get update && apt-get -y dist-upgrade
apt-get install -y pkg-config python3-dev gcc libvirt-dev python3-venv
python3 -m venv .env && source ./.env/bin/activate && pip install --upgrade pip && pip install -r requirements.txt

ssh-keygen -t rsa -b 4096 -N "" -f ~/.ssh/webvmcontrol

[ -d ~/.ssh ] || mkdir -p ~/.ssh
cat >> ~/.ssh/config << "EOF1"
Host kvmhost225
    HostName 192.168.10.225
    User webvmcontrol
    IdentityFile ~/.ssh/webvmcontrol
    Port 22
EOF1

echo "Copy and paste this content to every kvm host:"
echo "---"
echo ""
cat ~/.ssh/webvmcontrol.pub
echo ""
echo "---"
