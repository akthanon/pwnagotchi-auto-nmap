import os
import threading
import logging
import io
import zipfile
from flask import Flask, send_from_directory, abort, request, redirect, send_file
import pwnagotchi.plugins as plugins

class FileWebServerPlugin(plugins.Plugin):
    __author__ = '@jorge'
    __version__ = '1.3'
    __license__ = 'GPL3'
    __description__ = 'Servidor web bonito para ver, editar y descargar archivos desde la Raspberry Pi'

    def __init__(self):
        self.web_thread = None
        self.app = Flask(__name__)
        self.directories = {
            'files_nmap': '/home/pi/files_nmap',
            'auto_nmap': '/home/pi/auto_nmap',
            'handshakes': '/home/pi/handshakes'
        }

        self.style = """
        <style>
        body {
            font-family: Arial, sans-serif;
            background-color: #f4f4f4;
            margin: 0;
            padding: 20px;
        }
        h2, h3 {
            color: #333;
        }
        ul {
            list-style-type: none;
            padding: 0;
        }
        li {
            background: #fff;
            margin: 5px 0;
            padding: 10px;
            border-left: 5px solid #3498db;
            box-shadow: 0 2px 4px rgba(0,0,0,0.1);
        }
        a {
            text-decoration: none;
            color: #3498db;
            margin-right: 10px;
        }
        a:hover {
            text-decoration: underline;
        }
        pre {
            background: #222;
            color: #0f0;
            padding: 15px;
            overflow-x: auto;
        }
        textarea {
            width: 100%;
            height: 500px;
            font-family: monospace;
            font-size: 14px;
        }
        input[type=submit] {
            background-color: #3498db;
            color: white;
            padding: 10px 20px;
            border: none;
            cursor: pointer;
            margin-top: 10px;
        }
        input[type=submit]:hover {
            background-color: #2980b9;
        }
        p a.download-all {
            font-weight: bold;
            color: #d35400;
            font-size: 1.1em;
        }
        </style>
        """

        @self.app.route('/')
        def index():
            html = f"<h2>📁 Archivos disponibles</h2><ul>"
            for name in self.directories:
                html += f'<li><a href="/list/{name}">{name}</a></li>'
            html += "</ul>"
            return self.style + html

        @self.app.route('/list/<folder>')
        def list_files(folder):
            if folder not in self.directories:
                return abort(404)
            path = self.directories[folder]
            if not os.path.exists(path):
                os.makedirs(path)
            files = os.listdir(path)
            files.sort()
            html = f"""
            <h3>📂 Archivos en: {folder}</h3>
            <p><a class="download-all" href="/download_all/{folder}">⬇️ Descargar todo (ZIP)</a></p>
            <ul>
            """
            for f in files:
                html += (
                    f'<li><strong>{f}</strong><br>'
                    f'<a href="/download/{folder}/{f}">⬇️ Descargar</a>'
                    f'<a href="/view/{folder}/{f}">👁️ Ver</a>'
                    f'<a href="/edit/{folder}/{f}">✏️ Editar</a></li>'
                )
            html += "</ul><a href='/'>← Volver</a>"
            return self.style + html

        @self.app.route('/download/<folder>/<filename>')
        def download_file(folder, filename):
            if folder not in self.directories:
                return abort(404)
            directory = self.directories[folder]
            filepath = os.path.join(directory, filename)
            if not os.path.exists(filepath):
                return abort(404)
            return send_from_directory(directory, filename, as_attachment=True)

        @self.app.route('/download_all/<folder>')
        def download_all(folder):
            if folder not in self.directories:
                return abort(404)
            directory = self.directories[folder]
            if not os.path.exists(directory):
                return abort(404)

            zip_buffer = io.BytesIO()
            with zipfile.ZipFile(zip_buffer, 'w', zipfile.ZIP_DEFLATED) as zipf:
                for root, _, files in os.walk(directory):
                    for file in files:
                        filepath = os.path.join(root, file)
                        arcname = os.path.relpath(filepath, start=directory)
                        zipf.write(filepath, arcname)
            zip_buffer.seek(0)
            return send_file(
                zip_buffer,
                mimetype='application/zip',
                download_name=f"{folder}_all_files.zip",
                as_attachment=True
            )

        @self.app.route('/view/<folder>/<filename>')
        def view_file(folder, filename):
            if folder not in self.directories:
                return abort(404)
            filepath = os.path.join(self.directories[folder], filename)
            if not os.path.isfile(filepath):
                return abort(404)
            try:
                with open(filepath, "r", encoding="utf-8", errors="replace") as f:
                    content = f.read()
                html = f"<h3>👁️ Viendo: {filename}</h3><pre>{content}</pre>"
                html += f"<a href='/list/{folder}'>← Volver</a>"
                return self.style + html
            except Exception as e:
                return self.style + f"<p>⚠️ Error leyendo archivo: {e}</p><a href='/list/{folder}'>← Volver</a>"

        @self.app.route('/edit/<folder>/<filename>', methods=['GET', 'POST'])
        def edit_file(folder, filename):
            if folder not in self.directories:
                return abort(404)
            filepath = os.path.join(self.directories[folder], filename)
            if not os.path.isfile(filepath):
                return abort(404)

            if request.method == 'POST':
                new_content = request.form.get('content')
                try:
                    with open(filepath, "w", encoding="utf-8") as f:
                        f.write(new_content)
                    return redirect(f"/view/{folder}/{filename}")
                except Exception as e:
                    return self.style + f"<p>⚠️ Error guardando archivo: {e}</p><a href='/list/{folder}'>← Volver</a>"

            try:
                with open(filepath, "r", encoding="utf-8", errors="replace") as f:
                    content = f.read()
                html = f"""
                <h3>✏️ Editando: {filename}</h3>
                <form method="POST">
                    <textarea name="content">{content}</textarea><br>
                    <input type="submit" value="Guardar cambios">
                </form>
                <a href="/list/{folder}">← Cancelar</a>
                """
                return self.style + html
            except Exception as e:
                return self.style + f"<p>⚠️ Error abriendo archivo: {e}</p><a href='/list/{folder}'>← Volver</a>"

    def start_web_server(self):
        logging.info("[web_file_server] Iniciando servidor web en puerto 9666")
        self.app.run(host='0.0.0.0', port=9666, debug=False, use_reloader=False)

    def on_loaded(self):
        if self.web_thread is None:
            self.web_thread = threading.Thread(target=self.start_web_server, daemon=True)
            self.web_thread.start()
            logging.info("[web_file_server] Servidor web iniciado correctamente en http://<tu-ip>:9666")

    def on_unload(self, ui):
        logging.info("[web_file_server] Plugin descargado (el servidor Flask continúa en background)")
