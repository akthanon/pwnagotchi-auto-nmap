import os
import threading
import logging
from flask import Flask, send_from_directory, abort
import pwnagotchi.plugins as plugins

class FileWebServerPlugin(plugins.Plugin):
    __author__ = '@jorge'
    __version__ = '1.0'
    __license__ = 'GPL3'
    __description__ = 'Servidor web para descargar archivos desde la Raspberry Pi'

    def __init__(self):
        self.web_thread = None
        self.app = Flask(__name__)
        self.directories = {
            'files_nmap': '/home/pi/files_nmap',
            'auto_nmap': '/home/pi/auto_nmap',
            'handshakes': '/home/pi/handshakes'
        }

        @self.app.route('/')
        def index():
            html = "<h2>Archivos disponibles:</h2><ul>"
            for name in self.directories:
                html += f'<li><a href="/list/{name}">{name}</a></li>'
            html += "</ul>"
            return html

        @self.app.route('/list/<folder>')
        def list_files(folder):
            if folder not in self.directories:
                return abort(404)
            path = self.directories[folder]
            if not os.path.exists(path):
                os.makedirs(path)
            files = os.listdir(path)
            files.sort()
            html = f"<h3>Archivos en {folder}:</h3><ul>"
            for f in files:
                html += f'<li><a href="/download/{folder}/{f}">{f}</a></li>'
            html += "</ul><a href='/'>Volver</a>"
            return html

        @self.app.route('/download/<folder>/<filename>')
        def download_file(folder, filename):
            if folder not in self.directories:
                return abort(404)
            directory = self.directories[folder]
            filepath = os.path.join(directory, filename)
            if not os.path.exists(filepath):
                return abort(404)
            return send_from_directory(directory, filename, as_attachment=True)

    def start_web_server(self):
        logging.info("[web_file_server] Iniciando servidor web en puerto 9666")
        self.app.run(host='0.0.0.0', port=9666, debug=False, use_reloader=False)

    def on_loaded(self):
        if self.web_thread is None:
            self.web_thread = threading.Thread(target=self.start_web_server, daemon=True)
            self.web_thread.start()
            logging.info("[web_file_server] Servidor web iniciado correctamente.")

    def on_unload(self, ui):
        logging.info("[web_file_server] Plugin descargado (el servidor Flask continuará hasta que se detenga el proceso).")
