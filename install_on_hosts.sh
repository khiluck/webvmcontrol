#!/bin/bash
useradd -m webvmcontrol
echo "webvmcontrol:$(openssl rand -base64 12)" | sudo chpasswd
[ -d /etc/polkit-1/rules.d ] || mkdir -p /etc/polkit-1/rules.d
cat >> /etc/polkit-1/rules.d/50-webvmcontrol-libvirt.rules << "EOF2"
polkit.addRule(function(action, subject) {
    if (subject.user == "webvmcontrol" &&
        (action.id == "org.libvirt.unix.manage" ||
         action.id == "org.libvirt.unix.monitor")) {
        return polkit.Result.YES;
    }
})
EOF2

systemctl restart polkit

[ -d /home/webvmcontrol/.ssh ] || mkdir -p /home/webvmcontrol/.ssh
vi /home/webvmcontrol/.ssh/authorized_keys
