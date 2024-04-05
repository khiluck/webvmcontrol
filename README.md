# On the webserver:
# =================

# Generate ssh-key:
ssh-keygen -t rsa -b 4096 -N "" -f ~/.ssh/webvmcontrol

# Create ssh config file:
vi ~/.ssh/config
# ===
Host kvmhost225
    HostName 192.168.10.225
    User webvmcontrol
    IdentityFile ~/.ssh/webvmcontrol
    Port 22
# ===

# Add this content to every kvm host
cat ~/.ssh/webvmcontrol.pub


# On the kvmhosts:
# ================

# Add user
useradd -m webvmcontrol

# Set the random password for it
echo "webvmcontrol:$(openssl rand -base64 12)" | sudo chpasswd

# Limit user permissions only for some commands
vi /etc/polkit-1/rules.d/50-webvmcontrol-libvirt.rules
# ===
polkit.addRule(function(action, subject) {
    if (subject.user == "webvmcontrol" &&
        (action.id == "org.libvirt.unix.manage" ||
         action.id == "org.libvirt.unix.monitor")) {
        return polkit.Result.YES;
    }
})
# ===

# Add ssh pub key to user kvmmanager
mkdir /home/webvmcontrol/.ssh
vi /home/webvmcontrol/.ssh/authorized_keys
