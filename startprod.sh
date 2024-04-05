#!/bin/bash
source .env/bin/activate && gunicorn --env LOGIN_USER=$1 --env PASSW_USER=$2 app:app