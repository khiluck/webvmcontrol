from flask import Flask, render_template, request, redirect, url_for, send_file
import libvirt
import os
import tempfile

app = Flask(__name__)

def load_uris_from_config(config_path):
    uris = []
    with open(config_path, 'r') as file:
        uris = [line.strip() for line in file.readlines() if line.strip()]
    return uris

# Загрузка списка URI из конфигурационного файла
uris = load_uris_from_config('config.txt')

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
    vms = list_vms()
    return render_template('index.html', vms=vms)

@app.route('/reboot', methods=['POST'])
def reboot():
    vm_name = request.form['name']
    host_uri = request.form['host']
    conn = libvirt.open(host_uri)  # Используйте URI, полученный из формы
    if conn is not None:
        domain = conn.lookupByName(vm_name)
        domain.reboot(libvirt.VIR_DOMAIN_REBOOT_DEFAULT)
        conn.close()
    return redirect(url_for('index'))

@app.route('/destroy', methods=['POST'])
def destroy():
    vm_name = request.form['name']
    host_uri = request.form['host']
    conn = libvirt.open(host_uri)  # Используйте URI, полученный из формы
    if conn is not None:
        domain = conn.lookupByName(vm_name)
        domain.destroy()
        conn.close()
    return redirect(url_for('index'))

@app.route('/start', methods=['POST'])
def start():
    vm_name = request.form['name']
    host_uri = request.form['host']
    conn = libvirt.open(host_uri)
    if conn != None:
        domain = conn.lookupByName(vm_name)
        if not domain.isActive():
            domain.create()
        conn.close()
    return redirect(url_for('index'))

@app.route('/screenshot')
def screenshot():
    vm_name = request.args.get('name')
    host_uri = request.args.get('host')
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
