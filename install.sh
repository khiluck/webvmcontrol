#!/bin/bash
apt-get install -y pkg-config python3-dev gcc libvirt-dev python3-venv
python3 -m venv .env && source ./.env/bin/activate && pip install --upgrade pip && pip install -r requirements.txt
