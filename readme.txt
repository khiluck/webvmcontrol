# Start prod server:
# gunicorn doesn't work with evn variables???
gunicorn --env LOGIN_USER=loginuser --env PASSW_USER=password app:app




## DEV ###

# Set the environmental variables before starting app!
export LOGIN_USER=loginuser
export PASSW_USER=password

# Start dev server:
python app.py



