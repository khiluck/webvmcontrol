from flask import Flask, render_template, request, redirect, url_for, send_file, abort, make_response, request
from flask_login import LoginManager, UserMixin, login_user, login_required, logout_user, current_user
import libvirt
import os
import secrets
import tempfile
import datetime
import logging
from datetime import datetime
from urllib.parse import unquote, urlparse
from PIL import Image, ImageOps
import io


app = Flask(__name__)
app.secret_key = secrets.token_hex(16)  # Generates a 16-byte (128-bit) hex string



login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'

class User(UserMixin):
    def __init__(self, id, username, password):
        self.id = id
        self.username = username
        self.password = password

users = [User(id="1", username=os.environ.get('LOGIN_USER'), password=os.environ.get('PASSW_USER'))]
#print(os.environ.get('LOGIN_USER'))
#print(os.environ.get('PASSW_USER'))

log_directory = 'logs'
# Ensure log directory exists
if not os.path.exists(log_directory):
    os.makedirs(log_directory)
# Generate a timestamp
log_file_name = os.path.join(log_directory, "vm_actions.log")

# Basic configuration for logging
logging.basicConfig(filename=log_file_name, level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')

@login_manager.user_loader
def load_user(user_id):
    for user in users:
        if user.id == user_id:
            return user
    return None

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        user = next((user for user in users if user.username == username and user.password == password), None)
        if user:
            # Log successfull login here
            ip_address = request.remote_addr  # Get IP address of the client
            user_agent = request.headers.get('User-Agent')  # Optional: Capture user agent for more context
            logging.info(f"Successful login for username: {username} from IP: {ip_address} User-Agent: {user_agent}")
            login_user(user)
            return redirect(url_for('index'))
        else:
            # Log failed login attempt here
            ip_address = request.remote_addr  # Get IP address of the client
            user_agent = request.headers.get('User-Agent')  # Optional: Capture user agent for more context
            logging.warning(f"Failed login attempt for username: {username} from IP: {ip_address} User-Agent: {user_agent}")
            error_message = "Invalid username or password. Please try again."
            return render_template('login.html', error=error_message)
    else:
        return render_template('login.html')

@app.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('index'))


def load_uris_from_config(config_path):
    uris = []
    with open(config_path, 'r') as file:
        uris = [line.strip() for line in file.readlines() if line.strip()]
    return uris

# Загрузка списка URI из конфигурационного файла
uris = load_uris_from_config('servers.list')

def is_valid_uri(uri):
    parsed_uri = urlparse(uri)
    # Check if the scheme (driver name) part of the URI is present
    return bool(parsed_uri.scheme)

def ensure_valid_uri(uri):
    # If the URI is already valid, return it as is
    if is_valid_uri(uri):
        return uri
    # If the URI is just a hostname, construct a default URI (adjust this as needed)
    # Here assuming qemu+ssh and appending '/system' as it's common for QEMU connections
    return f"qemu+ssh://{uri}/system"

def extract_hostname(uri):
    parsed_uri = urlparse(uri)
    # Extract the hostname from the parsed URI; handle cases without SSH correctly
    hostname = parsed_uri.hostname if parsed_uri.hostname else parsed_uri.path
    return hostname

def list_vms_grouped_by_host():
    vms_grouped = {}
    for uri in uris:
        valid_uri = ensure_valid_uri(uri)  # Ensure the URI is valid
        conn = libvirt.open(valid_uri)
        if conn is None:
            print(f"Failed to open connection to {valid_uri}")
            continue
        domains = conn.listAllDomains()
        hostname = extract_hostname(valid_uri)  # Use the valid URI
        vms = [{
            "name": domain.name(),
            "status": "Running" if domain.isActive() else "Stopped",
            "host": hostname  # Use the extracted hostname
        } for domain in domains]
        vms_grouped[hostname] = vms
        conn.close()
    return vms_grouped


# Функция для получения списка ВМ
def list_vms():
    vms = []
    for uri in uris:
        conn = libvirt.open(uri)
        if conn is None:
            print(f"Failed to open connection to {uri}")
            continue
        domains = conn.listAllDomains()
        for domain in domains:
            vms.append({
                "name": domain.name(),
                "status": "Running" if domain.isActive() else "Stopped",
                "host": uri
            })
        conn.close()
    return vms

@app.route('/')
@login_required
def index():
    vms_grouped = list_vms_grouped_by_host()
    return render_template('index.html', vms_grouped=vms_grouped)

@app.route('/set_cookie')
def set_cookie():
    resp = make_response("Cookie is set")
    resp.set_cookie('your_cookie_name', 'cookie_value')
    return resp

@app.route('/get_cookie')
def get_cookie():
    cookie_value = request.cookies.get('your_cookie_name', 'Default_Value')
    return 'The value of the cookie is: ' + cookie_value

@app.route('/set_cookie_with_expiry')
def set_cookie_with_expiry():
    resp = make_response("Cookie with expiry is set")
    expire_time = datetime.datetime.now() + datetime.timedelta(days=1)  # Expires in 1 day
    resp.set_cookie('your_expiring_cookie', 'expiring_value', expires=expire_time)
    resp.set_cookie('secure_cookie', 'secure_value', secure=True, httponly=True)
    return resp

@app.route('/reboot', methods=['POST'])
@login_required
def reboot():
    vm_name = request.form['name']
    host_uri = request.form['host']
    user_agent = request.headers.get('User-Agent')
    ip_address = request.remote_addr
    # Example log message
    logging.info(f"User {current_user.username} initiated VM reboot for {vm_name} from IP {ip_address} with browser {user_agent}")

    # Ensure the URI is complete
    parsed_uri = urlparse(host_uri)
    if not parsed_uri.scheme:
        # Assuming qemu+ssh as default protocol and driver, adjust as necessary
        host_uri = f"qemu+ssh://{host_uri}/system"

    try:
        conn = libvirt.open(host_uri)
        if conn is not None:
            domain = conn.lookupByName(vm_name)
            domain.reboot(libvirt.VIR_DOMAIN_REBOOT_DEFAULT)
            conn.close()
    except libvirt.libvirtError as e:
        print(f"Failed to reboot VM {vm_name} on host {host_uri}: {e}")
        # Handle error appropriately, maybe return an error message to the user

    return redirect(url_for('index'))



@app.route('/destroy', methods=['POST'])
@login_required
def destroy():
    vm_name = request.form['name']
    host_uri = request.form['host']
    user_agent = request.headers.get('User-Agent')
    ip_address = request.remote_addr
    # Example log message
    logging.info(f"User {current_user.username} initiated VM power off for {vm_name} from IP {ip_address} with browser {user_agent}")

    # Ensure the URI is complete
    parsed_uri = urlparse(host_uri)
    if not parsed_uri.scheme:
        # Assuming qemu+ssh as default protocol and driver, adjust as necessary
        host_uri = f"qemu+ssh://{host_uri}/system"

    try:
        conn = libvirt.open(host_uri)
        if conn is not None:
            domain = conn.lookupByName(vm_name)
            domain.destroy()
            conn.close()
    except libvirt.libvirtError as e:
        print(f"Failed to forcely shutdown VM {vm_name} on host {host_uri}: {e}")
        # Handle error appropriately, maybe return an error message to the user

    return redirect(url_for('index'))



@app.route('/start', methods=['POST'])
@login_required
def start():
    vm_name = request.form['name']
    host_uri = request.form['host']
    user_agent = request.headers.get('User-Agent')
    ip_address = request.remote_addr
    # Example log message
    logging.info(f"User {current_user.username} initiated VM start for {vm_name} from IP {ip_address} with browser {user_agent}")

    # Ensure the URI is complete
    parsed_uri = urlparse(host_uri)
    if not parsed_uri.scheme:
        # Assuming qemu+ssh as default protocol and driver, adjust as necessary
        host_uri = f"qemu+ssh://{host_uri}/system"

    try:
        conn = libvirt.open(host_uri)
        if conn != None:
            domain = conn.lookupByName(vm_name)
            if not domain.isActive():
                domain.create()
            conn.close()
    except libvirt.libvirtError as e:
        print(f"Failed to start VM {vm_name} on host {host_uri}: {e}")

    return redirect(url_for('index'))

@app.route('/screenshot')
@login_required
def screenshot():
    vm_name = request.args.get('name')
    host_uri = unquote(request.args.get('host'))

    # Ensure the URI is complete
    parsed_uri = urlparse(host_uri)
    if not parsed_uri.scheme:
        # Assuming qemu+ssh as default protocol and driver, adjust as necessary
        host_uri = f"qemu+ssh://{host_uri}/system"

    try:
        conn = libvirt.open(host_uri)
        if conn is not None:
            domain = conn.lookupByName(vm_name)
            with tempfile.NamedTemporaryFile(delete=True, suffix='.png') as tmpfile:
                # Создание объекта stream
                stream = conn.newStream(0)
                # Получение скриншота
                domain.screenshot(stream, 0)
                # Сохранение данных из stream во временный файл
                def handler(stream, buf, opaque):
                    tmpfile.write(buf)
                    return 0
                stream.recvAll(handler, None)
                stream.finish()
                tmpfile.flush()
                # Resize the image using Pillow with the correct resampling filter
                with Image.open(tmpfile.name) as img:
                    resized_img = img.resize((640, 480), Image.Resampling.LANCZOS)
                    img_byte_arr = io.BytesIO()
                    resized_img.save(img_byte_arr, format='PNG')
                    img_byte_arr.seek(0)  # Reset the file pointer to the beginning of the byte array

                # Return the resized image to the client with the correct parameters
                return send_file(
                    img_byte_arr,
                    mimetype='image/png',
                    as_attachment=True,
                    download_name='screenshot.png'
                )
                # Resize the image using Pillow
                with Image.open(tmpfile.name) as img:
                    resized_img = img.resize((640, 480), Image.Resampling.LANCZOS)
                    img_byte_arr = io.BytesIO()
                    resized_img.save(img_byte_arr, format='PNG')
                    img_byte_arr = img_byte_arr.getvalue()

                # Return the resized image to the client
                return send_file(
                    io.BytesIO(img_byte_arr),
                    attachment_filename='screenshot.png',
                    mimetype='image/png'
                )
    except libvirt.libvirtError as e:
        return str(e), 500
    finally:
        if 'conn' in locals() and conn is not None:
            conn.close()
    return 'Screenshot not available', 404

if __name__ == '__main__':
    app.run(debug=True)
    #app.run(debug=True, host='0.0.0.0')
