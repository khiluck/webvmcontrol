# Set the environmental variables before starting app!
export LOGIN_USER=loginuser
export PASSW_USER=password(.env)

# Start prod server:
gunicorn -w 4 app:app

# Start dev server:
python app.py