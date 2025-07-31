from pwnagotchi.ui.components import Text
from pwnagotchi.ui.view import BLACK
import pwnagotchi.ui.fonts as fonts
import pwnagotchi.plugins as plugins
import logging
import os
import subprocess
import time
import datetime
import threading

import json

FILES_DIR = "/home/pi/files_nmap"
NOSCAN_FILE = os.path.join(FILES_DIR, "ssid_noscan.txt")
KNOWN_FILE = os.path.join(FILES_DIR, "ssid_known.json")

def load_ssid_data():
    global SSID_NOSCAN, SSID_KNOWN

    if not os.path.exists(FILES_DIR):
        os.makedirs(FILES_DIR)
    
    if not os.path.exists(NOSCAN_FILE):
        with open(NOSCAN_FILE, "w") as f:
            f.write("Club_Totalplay_WiFi\nMegacable Gratis\nCASINO_HERMOSILLO\n")
    
    if not os.path.exists(KNOWN_FILE):
        with open(KNOWN_FILE, "w") as f:
            f.write("Totalplay-CCCX PASSWORD123\nMiRedCasa123 pa55w0rd\nCafeteriaLibre 12345678\n")  # ejemplo

    try:
        with open(NOSCAN_FILE, "r") as f:
            SSID_NOSCAN = [line.strip() for line in f if line.strip()]
    except Exception as e:
        logging.error(f"No se pudo cargar {NOSCAN_FILE}: {e}")
        SSID_NOSCAN = []

    try:
        SSID_KNOWN = {}
        with open(KNOWN_FILE, "r") as f:
            for line in f:
                parts = line.strip().split(None, 1)  # separa solo en 2 partes: SSID y contraseña
                if len(parts) == 2:
                    ssid, password = parts
                    SSID_KNOWN[ssid] = password
    except Exception as e:
        logging.error(f"No se pudo cargar {KNOWN_FILE}: {e}")
        SSID_KNOWN = {}

READY = 0

class ScannerPlugin(plugins.Plugin):
    __author__ = '@jorge'
    __version__ = '2.1'
    __license__ = 'GPL3'
    __description__ = 'Muestra un mensaje en pantalla y escanea redes abiertas o conocidas con wlan1'

    load_ssid_data()

    def __init__(self):
        self.message = "  NMAP Plugin"
        self.scanned_ssids = set()
        self.lock = threading.Lock()
        self.scanning = False

    def on_loaded(self):
        global READY
        logging.info("HelloWorldScannerPlugin cargado")
        READY = 1

    def _interface_exists(self, interface):
        return os.path.exists(f'/sys/class/net/{interface}')

    def _connect_to_open_network(self, ssid, interface="wlan1"):
        if ssid in SSID_NOSCAN:
            return False

        logging.info(f"Intentando conectarse a la red abierta SSID: {ssid}")
        config = f"""
        network={{
            ssid=\"{ssid}\"
            key_mgmt=NONE
        }}
        """
        with open("/tmp/open.conf", "w") as f:
            f.write(config)

        try:
            subprocess.run(["wpa_supplicant", "-B", "-i", interface, "-c", "/tmp/open.conf"], check=True)
            time.sleep(5)
            subprocess.run(["dhclient", interface], check=True)
            logging.info(f"Conectado a {ssid} en {interface}")
            return True
        except subprocess.CalledProcessError as e:
            logging.error(f"Error al conectar a {ssid}: {e}")
            return False

    def _connect_to_known_network(self, ssid, password, interface="wlan1"):
        logging.info(f"Intentando conectarse a red conocida SSID: {ssid}")
        config = f"""
        network={{
            ssid=\"{ssid}\"
            psk=\"{password}\"
        }}
        """
        with open("/tmp/known.conf", "w") as f:
            f.write(config)

        try:
            subprocess.run(["wpa_supplicant", "-B", "-i", interface, "-c", "/tmp/known.conf"], check=True)
            time.sleep(5)
            subprocess.run(["dhclient", interface], check=True)
            logging.info(f"Conectado a red conocida {ssid}")
            return True
        except subprocess.CalledProcessError as e:
            logging.error(f"Error al conectar a red conocida {ssid}: {e}")
            return False

    def _disconnect(self, interface="wlan1"):
        logging.info(f"Desconectando {interface}")
        subprocess.run(["dhclient", "-r", interface], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        subprocess.run(["pkill", "-f", f"wpa_supplicant.*{interface}"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        subprocess.run(["ip", "link", "set", interface, "down"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        time.sleep(1)
        subprocess.run(["ip", "link", "set", interface, "up"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

    def _run_nmap_scan(self, interface="wlan1", ssid="unknown"):
        try:
            ip_output = subprocess.check_output(["ip", "addr", "show", interface]).decode()
            ip_line = [line.strip() for line in ip_output.splitlines() if "inet " in line]
            if not ip_line:
                logging.warning(f"No se pudo obtener IP en {interface}")
                return False
            ip = ip_line[0].split()[1]
            subnet = ip.split('/')[1]
            network = ip.split('/')[0].rsplit('.', 1)[0] + ".0/" + subnet

            logging.info(f"Escaneando la red: {network}")

            os.makedirs("/home/pi/auto_nmap", exist_ok=True)
            fecha = datetime.datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
            ssid_safe = ssid.replace(" ", "_").replace("/", "_")
            log_file = f"/home/pi/auto_nmap/nmap_scan_{ssid_safe}_{fecha}.log"

            with open(log_file, "w") as f:
                subprocess.run(["nmap", "-T4", "-F", network], stdout=f, stderr=subprocess.STDOUT, check=True)

            logging.info(f"Escaneo guardado en {log_file}")
            return True
        except Exception as e:
            logging.error(f"Error ejecutando nmap: {e}")
            return False

    def _connect_and_scan(self, ssid, password, agent, is_known):
        with self.lock:
            if self.scanning:
                return
            self.scanning = True

        try:
            self.message = f"[~]:{ssid[:14]}"
            agent.view().update(force=True)
            success = self._run_nmap_scan(ssid=ssid)
            if success:
                self.scanned_ssids.add(ssid)
                self.message = f"[O]:{ssid[:14]}"
            else:
                self.message = f"[X]:{ssid[:14]}"
            agent.view().update(force=True)
        finally:
            self._disconnect()
            with self.lock:
                self.scanning = False

    def on_unfiltered_ap_list(self, agent, access_points):
        global READY
        if not READY:
            return

        if not hasattr(self, "wlan_missing"):
            self.wlan_missing = False

        if not self._interface_exists("wlan1"):
            if not self.wlan_missing:
                logging.warning("¡El adaptador wlan1 ha sido desconectado!")
                self.message = "  wifi: False"
                self.wlan_missing = True
            return
        else:
            if self.wlan_missing:
                logging.info("El adaptador wlan1 ha sido reconectado.")
                self.message = "  wifi: True"
                self.wlan_missing = False

        if self.scanning:
            return

        for ssid, password in SSID_KNOWN.items():
            if ssid in self.scanned_ssids:
                continue
            matching_aps = [ap for ap in access_points if (ap.get("hostname") or ap.get("ssid")) == ssid]
            if not matching_aps:
                continue
            if self._connect_to_known_network(ssid, password):
                threading.Thread(target=self._connect_and_scan, args=(ssid, password, agent, True)).start()
                return

        open_networks = [
            ap for ap in access_points
            if ap.get("encryption", "unknown").lower() in ["open", "none"]
        ]

        new_networks = [
            ap for ap in open_networks
            if (ap.get("hostname") or ap.get("ssid")) not in self.scanned_ssids
        ]

        if not new_networks:
            logging.info("Todas las redes ya fueron escaneadas en esta sesión.")
            self.message = "  Buscando..."
            return

        for ap in new_networks:
            ssid = ap.get("hostname") or ap.get("ssid")

            if ssid in SSID_NOSCAN:
                logging.info(f"Descartando red abierta: {ssid}")
                self.message = "  Buscando..."
                continue

            if not ssid or ssid in self.scanned_ssids or ssid in SSID_NOSCAN:
                continue

            if self._connect_to_open_network(ssid):
                threading.Thread(target=self._connect_and_scan, args=(ssid, None, agent, False)).start()
                break

    def on_ui_setup(self, ui):
        if ui.is_waveshare_v2():
            position = (120, 5)
        elif ui.is_waveshare_v1():
            position = (115, 5)
        elif ui.is_waveshare144lcd():
            position = (30, 5)
        elif ui.is_inky():
            position = (105, 5)
        elif ui.is_waveshare2in7():
            position = (150, 5)
        elif ui.is_waveshare1in54V2():
            position = (40, 5)
        else:
            position = (85, 0)

        ui.add_element(
            'hello_status',
            Text(
                color=BLACK,
                value=self.message,
                position=position,
                font=fonts.Small,
            )
        )

    def on_ui_update(self, ui):
        with ui._lock:
            ui.set('hello_status', self.message)

    def on_unload(self, ui):
        with ui._lock:
            ui.remove_element('hello_status')
