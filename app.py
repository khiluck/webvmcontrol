from flask import Flask, render_template, request, redirect, url_for, send_file
import libvirt
import os
import tempfile
from urllib.parse import unquote, urlparse

app = Flask(__name__)

def load_uris_from_config(config_path):
    uris = []
    with open(config_path, 'r') as file:
        uris = [line.strip() for line in file.readlines() if line.strip()]
    return uris

# Загрузка списка URI из конфигурационного файла
uris = load_uris_from_config('config.txt')

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
def index():
    vms_grouped = list_vms_grouped_by_host()
    return render_template('index.html', vms_grouped=vms_grouped)

#@app.route('/reboot', methods=['POST'])
#def reboot():
#    vm_name = request.form['name']
#    host_uri = request.form['host']
#    conn = libvirt.open(host_uri)  # Используйте URI, полученный из формы
#    if conn is not None:
#        domain = conn.lookupByName(vm_name)
#        domain.reboot(libvirt.VIR_DOMAIN_REBOOT_DEFAULT)
#        conn.close()
#    return redirect(url_for('index'))



@app.route('/reboot', methods=['POST'])
def reboot():
    vm_name = request.form['name']
    host_uri = request.form['host']

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
def destroy():
    vm_name = request.form['name']
    host_uri = request.form['host']

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
def start():
    vm_name = request.form['name']
    host_uri = request.form['host']

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
def screenshot():
    vm_name = request.args.get('name')
#    host_uri = request.args.get('host')
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
                # Возвращение файла пользователю
                return send_file(tmpfile.name, mimetype='image/png', as_attachment=True)
    except libvirt.libvirtError as e:
        return str(e), 500
    finally:
        if 'conn' in locals() and conn is not None:
            conn.close()
    return 'Screenshot not available', 404

if __name__ == '__main__':
    app.run(debug=True)
    #app.run(debug=True, host='0.0.0.0')
