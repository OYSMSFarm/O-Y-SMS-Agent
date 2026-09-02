from flask import Flask, render_template, request, jsonify
from flask_cors import CORS
import serial.tools.list_ports
from sim_manager import ModemDriver
from database import init_db, get_all_sims, add_sim, update_sim_status

app = Flask(__name__)
CORS(app)
init_db()

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/api/sims', methods=['GET'])
def list_sims():
    sims = get_all_sims()
    return jsonify([dict(sim) for sim in sims])

@app.route('/api/sims/add', methods=['POST'])
def add_new_sim():
    data = request.json
    add_sim(
        imei=data['imei'],
        phone_number=data.get('phone_number', ''),
        provider=data['provider'],
        port=data['port'],
        ussd_code=data.get('ussd_code', '*100#')
    )
    return jsonify({'success': True})

@app.route('/api/modem/scan')
def scan_modems():
    ports = serial.tools.list_ports.comports()
    modem_list = []
    for port in ports:
        if 'USB' in port.description or 'Serial' in port.description:
            modem_list.append({
                'port': port.device,
                'description': port.description,
                'hwid': port.hwid
            })
    return jsonify(modem_list)

@app.route('/api/modem/probe/<port>')
def probe_modem(port):
    driver = ModemDriver(port)
    if driver.connect():
        imei = driver.get_imei()
        imsi = driver.get_imsi()
        iccid = driver.get_iccid()
        signal = driver.get_signal()
        network = driver.get_network()
        phone = driver.get_phone_number()
        driver.disconnect()
        
        if imei:
            update_sim_status(
                sim_id=imei,  # Use IMEI as ID for now
                status='online',
                signal=signal,
                network=network
            )
            return jsonify({
                'success': True,
                'imei': imei,
                'imsi': imsi,
                'iccid': iccid,
                'signal': signal,
                'network': network,
                'phone_number': phone
            })
        else:
            return jsonify({'success': False, 'error': 'No IMEI found'})
    else:
        return jsonify({'success': False, 'error': 'Connection failed'})

@app.route('/api/sims/<sim_id>/ussd')
def check_balance(sim_id):
    sim = get_all_sims()
    for s in sim:
        if s['id'] == int(sim_id):
            port = s['port']
            ussd_code = s['ussd_balance_code'] or '*100#'
            
            driver = ModemDriver(port)
            if driver.connect():
                response = driver.send_ussd(ussd_code)
                driver.disconnect()
                
                update_sim_status(
                    sim_id=s['id'],
                    status='online',
                    signal=driver.get_signal(),
                    network=driver.get_network()
                )
                
                return jsonify({
                    'success': True,
                    'response': response,
                    'raw': driver.send_at('AT+CUSD?')
                })
            else:
                return jsonify({'success': False, 'error': 'Connection failed'})
    
    return jsonify({'success': False, 'error': 'SIM not found'})

if __name__ == '__main__':
    app.run(debug=True, port=5000)