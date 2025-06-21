import os
import shutil
import sqlite3
import logging
import tempfile
import gc
from datetime import datetime, timedelta
from typing import List, Dict

logging.basicConfig(level=logging.INFO)

def chrome_time(chrome_time: int) -> str:
    if chrome_time == 0:
        return "N/A"
    epoch_start = datetime(1601, 1, 1)
    return (epoch_start + timedelta(microseconds=chrome_time)).strftime("%Y-%m-%d %H:%M:%S")

def browser_history(user_data_path: str, browser_name: str) -> List[Dict]:
    if not os.path.exists(user_data_path):
        logging.warning(f"[{browser_name}] path not found: {user_data_path}")
        return []

    result = []
    for root, _, files in os.walk(user_data_path):
        if "History" in files:
            full_history = os.path.join(root, "History")
            profile_name = os.path.basename(os.path.dirname(full_history))

            try:
                with tempfile.NamedTemporaryFile(delete=False, suffix=".db") as tmp_file:
                    shutil.copy2(full_history, tmp_file.name)
                    tmp_path = tmp_file.name

                # Force SQLite read-only mode
                uri_path = f'file:{tmp_path}?mode=ro'
                conn = sqlite3.connect(uri_path, uri=True)
                cursor = conn.cursor()
                cursor.execute("SELECT url, title, last_visit_time FROM urls")
                for url, title, last_visit in cursor.fetchall():
                    result.append({
                        "browser": browser_name,
                        "profile": profile_name,
                        "url": url,
                        "title": title,
                        "time": chrome_time(last_visit),
                        "timestamp": last_visit
                    })
                conn.close()
                gc.collect()  # Memastikan file handler benar-benar dilepas
                os.remove(tmp_path)

            except Exception as e:
                logging.error(f"[{browser_name}] Error Processing {profile_name}: {e}")
                try:
                    if os.path.exists(tmp_path):
                        os.remove(tmp_path)
                except Exception as del_err:
                    logging.warning(f"Gagal menghapus {tmp_path}: {del_err}")

    result.sort(key=lambda x: x["timestamp"], reverse=True)
    for item in result:
        item.pop("timestamp", None)

    return result[:10]

def all_history_browser() -> List[Dict]:
    browser_paths = {
        "Chrome": os.path.expandvars(r"%LOCALAPPDATA%\Google\Chrome\User Data"),
        "Edge": os.path.expandvars(r"%LOCALAPPDATA%\Microsoft\Edge\User Data"),
        "Brave": os.path.expandvars(r"%LOCALAPPDATA%\BraveSoftware\Brave-Browser\User Data"),
    }

    all_result = []
    for browser_name, path in browser_paths.items():
        try:
            all_result.extend(browser_history(path, browser_name))
        except Exception as e:
            logging.error(f"Gagal mengambil riwayat dari {browser_name}: {e}")

    return all_result
