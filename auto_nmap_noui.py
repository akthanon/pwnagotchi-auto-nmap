import logging
import os
import subprocess
import time
import datetime
import pwnagotchi.plugins as plugins

READY = 0
SSID_NOSCAN = ["SSID"]
SSID_KNOWN = {
    "SSID": "PASSWORD",
    # puedes añadir más redes aquí
}

class OpenNetworkScanner(plugins.Plugin):
    __author__ = '@nagy_craig modificado por @jorge'
    __version__ = '1.3'
    __license__ = 'GPL3'
    __description__ = 'Se conecta a redes abiertas con wlan1, escanea con nmap, guarda resultados y evita repetir escaneos'

    def __init__(self):
        self.scanned_ssids = set()

    def on_loaded(self):
        global READY
        logging.info("OpenNetworkScanner cargado")
        READY = 1

    def _interface_exists(self, interface):
        return os.path.exists(f'/sys/class/net/{interface}')

    def _is_connected(self, interface):
        iwconfig = os.popen(f'iwconfig {interface}').read()
        return "ESSID" in iwconfig and "Not-Associated" not in iwconfig

    def _connect_to_open_network(self, ssid, interface="wlan1"):
        if ssid in SSID_NOSCAN:
            logging.info(f"Descartando la red: {ssid}")
            return False
        logging.info(f"Intentando conectarse a la red abierta SSID: {ssid}")
        config = f"""
        network={{
            ssid="{ssid}"
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
            ssid="{ssid}"
            psk="{password}"
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

    def on_unfiltered_ap_list(self, agent, access_points):
        global READY
        if not READY:
            return

        if not self._interface_exists("wlan1"):
            if hasattr(self, "wlan_missing") and not self.wlan_missing:
                logging.warning("¡El adaptador wlan1 ha sido desconectado!")
                self.wlan_missing = True
            return
        else:
            if hasattr(self, "wlan_missing") and self.wlan_missing:
                logging.info("El adaptador wlan1 ha sido reconectado.")
                self.wlan_missing = False

        # Primero intenta redes conocidas (con contraseña)
        for ssid, password in SSID_KNOWN.items():
            if ssid in self.scanned_ssids:
                continue
            matching_aps = [ap for ap in access_points if (ap.get("hostname") or ap.get("ssid")) == ssid]
            if not matching_aps:
                continue

            if self._connect_to_known_network(ssid, password):
                if self._run_nmap_scan(ssid=ssid):
                    self.scanned_ssids.add(ssid)
                self._disconnect()
                return  # solo una red por ciclo

        # Luego escanea redes abiertas
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
            return

        for ap in new_networks:
            ssid = ap.get("hostname") or ap.get("ssid")
            if not ssid or ssid in self.scanned_ssids:
                continue
            if ssid in SSID_NOSCAN:
                logging.info(f"Descartando red abierta: {ssid}")
                continue

            if self._connect_to_open_network(ssid):
                if self._run_nmap_scan(ssid=ssid):
                    self.scanned_ssids.add(ssid)
                self._disconnect()
                break

