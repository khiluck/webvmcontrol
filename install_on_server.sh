#!/bin/bash

USRNAME=webvmcontrol
PATHTOAPP=/home/webvmcontrol

# Prepare the OS
apt-get update && apt-get -y dist-upgrade
apt-get install -y pkg-config python3-dev gcc libvirt-dev python3-venv nginx

# Create a user
useradd -m $USRNAME
echo "$USRNAME:$(openssl rand -base64 12)" | sudo chpasswd

[ -d /etc/polkit-1/rules.d ] || mkdir -p /etc/polkit-1/rules.d
[ -d /etc/polkit-1/localauthority/50-local.d ] || mkdir -p /etc/polkit-1/localauthority/50-local.d/

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

# Generate a ssh-key for this user
[ -d /home/$USRNAME/.ssh ] || mkdir -p /home/$USRNAME/.ssh

ssh-keygen -t rsa -b 4096 -N "" -f /home/$USRNAME/.ssh/webvmcontrol

cat >> /home/$USRNAME/.ssh/config << "EOF1"
Host kvmhost225
    HostName 192.168.10.225
    User $USRNAME
    IdentityFile /home/$USRNAME/.ssh/webvmcontrol
    Port 22
EOF1

# Copy the app
[ -d /$PATHTOAPP/webvmcontrol ] || mkdir -p /$PATHTOAPP/webvmcontrol
cp -r . /$PATHTOAPP/webvmcontrol

# Create an environment and install dependencies
python3 -m venv /$PATHTOAPP/webvmcontrol/.env && source /$PATHTOAPP/webvmcontrol/.env/bin/activate && pip install --upgrade pip && pip install -r requirements.txt

# Set the permissions
chown $USRNAME:$USRNAME -R /$PATHTOAPP/webvmcontrol
chown $USRNAME:$USRNAME -R /home/$USRNAME/.ssh
chmod 600 -R /home/$USRNAME/.ssh


# Prepare the nginx
[ -d /etc/nginx/certs ] || mkdir -p /etc/nginx/certs

cat >> /etc/nginx/conf.d/webvmcontrol.conf << "EOF"
server {
    listen 80;
    server_name vm.your.website;
    return 301 https://$server_name$request_uri;
        }

server {
    listen 443 ssl;
    server_name vm.your.website;

    ssl_certificate /etc/nginx/certs/_.your.website.crt;
    ssl_certificate_key /etc/nginx/certs/_.your.website.key;

    ssl_protocols TLSv1.2 TLSv1.3;
    ssl_prefer_server_ciphers on;
    ssl_ciphers "ECDHE-ECDSA-CHACHA20-POLY1305:ECDHE-RSA-CHACHA20-POLY1305:ECDHE-ECDSA-AES128-GCM-SHA256:ECDHE-RSA-AES128-GCM-SHA256:ECDHE-ECDSA-AES256-GCM-SHA384:ECDHE-RSA-AES256-GCM-SHA384:DHE-RSA-AES128-GCM-SHA256:DHE-RSA-AES256-GCM-SHA384";
    ssl_session_cache shared:SSL:50m;
    ssl_session_timeout 1d;
    ssl_session_tickets off;

    # HSTS (optional)
    #add_header Strict-Transport-Security "max-age=31536000" always;

    location / {
        proxy_pass http://127.0.0.1:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }

    # Add configuration for static files if needed
    }
EOF

# Add script to boot
cat << EOF2 > /usr/lib/systemd/system/webvmcontrol.service
[Unit]
Description=webvmcontrol
After=network.target libvirtd.service

[Service]
User=$USRNAME
EnvironmentFile=/$PATHTOAPP/webvmcontrol/cred.env
WorkingDirectory=/$PATHTOAPP/webvmcontrol/
ExecStart=/$PATHTOAPP/webvmcontrol/.env/bin/gunicorn app:app
Restart=always

[Install]
WantedBy=multi-user.target
EOF2
 
# Enable service
systemctl enable webvmcontrol.service


echo "Copy and paste this content to every kvm host:"
echo "---"
echo ""
cat /home/$USRNAME/.ssh/webvmcontrol.pub
echo ""
echo "---"
echo ""
echo "1. Copy your certs to /etc/nginx/certs folder and change the settings in /etc/nginx/conf.d/webvmcontrol.conf file!"
echo ""
echo "2. Edit /home/$USRNAME/.ssh/config file"
echo ""
echo "3. Edit /$PATHTOAPP/webvmcontrol/cred.env file and set login and password"
echo ""
echo "4. Edit /$PATHTOAPP/webvmcontrol/servers.list file and add remote KVMs"
echo ""
