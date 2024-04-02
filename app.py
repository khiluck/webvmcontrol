from flask import Flask, render_template, request, redirect, url_for
import libvirt

app = Flask(__name__)

# Функция для получения списка ВМ
def list_vms():
    conn = libvirt.open('qemu:///system')
    if conn == None:
        return []
    domains = conn.listAllDomains()
    vms = []
    for domain in domains:
        vms.append({
            "name": domain.name(),
            "status": "Running" if domain.isActive() else "Stopped"
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
    conn = libvirt.open('qemu:///system')
    if conn != None:
        domain = conn.lookupByName(vm_name)
        domain.reboot()
        conn.close()
    return redirect(url_for('index'))

@app.route('/reset', methods=['POST'])
def reset():
    vm_name = request.form['name']
    conn = libvirt.open('qemu:///system')
    if conn != None:
        domain = conn.lookupByName(vm_name)
        domain.reset()
        conn.close()
    return redirect(url_for('index'))

if __name__ == '__main__':
    app.run(debug=True)
