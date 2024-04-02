venv:
	SHELL := /bin/bash
	[[ -d .env ]] && { source ./.env/bin/activate; } || { python$1 -m venv .env; source ./.env/bin/activate; [[ -f requirements.txt ]] && pip install --upgrade pip; pip install -r requirements.txt; }