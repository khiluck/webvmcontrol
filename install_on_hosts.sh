#!/bin/bash
useradd -m webvmcontrol
echo "webvmcontrol:$(openssl rand -base64 12)" | sudo chpasswd
[ -d /etc/polkit-1/rules.d ] || mkdir -p /etc/polkit-1/rules.d

# For Debian 12
cat >> /etc/polkit-1/rules.d/50-webvmcontrol-libvirt.rules << "EOF2"
polkit.addRule(function(action, subject) {
    if (subject.user == "webvmcontrol" &&
        (action.id == "org.libvirt.unix.manage" ||
         action.id == "org.libvirt.unix.monitor")) {
        return polkit.Result.YES;
    }
})
EOF2

# For Debian 11
cat >> /etc/polkit-1/localauthority/50-local.d/50-webvmcontrol-libvirt.pkla << "EOF3"
[Grant webvmcontrol libvirt permissions]
Identity=unix-user:webvmcontrol
Action=org.libvirt.unix.manage;org.libvirt.unix.monitor
ResultAny=yes
ResultInactive=yes
ResultActive=yes
EOF3

systemctl restart polkit

[ -d /home/webvmcontrol/.ssh ] || mkdir -p /home/webvmcontrol/.ssh
vi /home/webvmcontrol/.ssh/authorized_keys
