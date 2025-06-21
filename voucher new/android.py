from kivy.app import App
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.label import Label
from kivy.uix.button import Button
from kivy.core.clipboard import Clipboard
import random
import string
import requests
from datetime import datetime

VOUCHER_SERVER = "http://192.168.20.15:5500/store-voucher"

def generate_voucher():
    def block():
        return ''.join(random.choices(string.ascii_uppercase + string.digits, k=4))
    return f"{block()}-{block()}-{block()}"

class VoucherApp(App):
    def build(self):
        self.voucher = generate_voucher()
        self.send_to_server(self.voucher)

        layout = BoxLayout(orientation='vertical', padding=20, spacing=10)
        label_title = Label(text="🎉 SELAMAT!", font_size=32)
        label_info = Label(text="Klaim Voucher Anda", font_size=20)
        self.label_voucher = Label(text=self.voucher, font_size=24, bold=True, color=(0, 1, 0, 1))

        btn_copy = Button(text="SALIN", size_hint=(1, 0.2), background_color=(0.2, 0.6, 1, 1))
        btn_copy.bind(on_press=self.copy_to_clipboard)

        layout.add_widget(label_title)
        layout.add_widget(label_info)
        layout.add_widget(self.label_voucher)
        layout.add_widget(btn_copy)

        return layout

    def copy_to_clipboard(self, instance):
        Clipboard.copy(self.voucher)
        instance.text = "✓ Disalin"

    def send_to_server(self, code):
        try:
            requests.post(VOUCHER_SERVER, json={"voucher_code": code})
            print(f"[INFO] Voucher dikirim: {code}")
        except Exception as e:
            print(f"[ERROR] Gagal kirim voucher: {e}")

if __name__ == '__main__':
    VoucherApp().run()
