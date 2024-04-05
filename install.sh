#!/bin/bash
apt-get install -y pkg-config python3-dev gcc libvirt-dev
[[ -d .env ]] && { source ./.env/bin/activate; } || { python3 -m venv .env; source ./.env/bin/activate; [[ -f requirements.txt ]] && pip install --upgrade pip; pip install -r requirements.txt; }

