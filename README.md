# 📡 Pwnagotchi Auto-Nmap

**Pwnagotchi Auto-Nmap** is a collection of Pwnagotchi plugins that automatically connect to open or known Wi-Fi networks using `wlan1`, run `nmap` scans on the discovered subnet, save the results, and provide a web interface to browse, download, view, and edit the generated files.

> ⚠️ **Legal warning:** Use this only on networks you own or have explicit permission to test. Unauthorized scanning is illegal in many jurisdictions.

---

## ✨ Features

- Automatically connects to open Wi-Fi networks with `wlan1`.
- Connects to known networks using credentials from `ssid_known.json`.
- Excludes networks listed in `ssid_noscan.txt`.
- Runs `nmap -T4 -F` on the detected subnet.
- Saves scan logs to `/home/pi/auto_nmap/`.
- Avoids rescanning the same SSID during a session.
- Shows status messages on the Pwnagotchi display (UI version).
- Detects if `wlan1` is disconnected/reconnected.
- Web file server on port `9666` to:
  - List files in `files_nmap`, `auto_nmap`, and `handshakes`.
  - Download individual files.
  - Download entire folders as ZIP.
  - View text files in the browser.
  - Edit text files directly from the web interface.

---

## 📁 Project Structure

```text
pwnagotchi-auto-nmap/
├── auto_nmap.py          # Main plugin with UI support
├── auto_nmap_noui.py     # Plugin without UI (headless)
├── auto_nmap_old.py      # Legacy version
├── file_downloader.py    # Simple web file server
├── file_editor.py        # Enhanced web server with view/edit/ZIP
└── README.md             # This file
```

---

## 📋 Requirements

- Pwnagotchi installed and running.
- Raspberry Pi (or compatible ARM device).
- External Wi-Fi adapter detected as `wlan1`.
- `nmap` installed.
- `wpa_supplicant`, `dhclient`, `ip`, `pkill`.
- Python 3 with `Flask`.
- Basic knowledge of Linux and Pwnagotchi plugins.

Install missing dependencies:

```bash
sudo apt update
sudo apt install -y nmap python3-flask wpasupplicant isc-dhcp-client
```

---

## 🚀 Installation

1. Copy the plugin files to your Pwnagotchi custom plugins directory:

```bash
sudo cp auto_nmap.py /usr/local/share/pwnagotchi/custom-plugins/
sudo cp file_editor.py /usr/local/share/pwnagotchi/custom-plugins/
```

2. Create the required directories and configuration files:

```bash
sudo mkdir -p /home/pi/files_nmap
sudo mkdir -p /home/pi/auto_nmap
sudo mkdir -p /home/pi/handshakes
```

3. Create `ssid_noscan.txt` (networks to ignore):

```bash
sudo nano /home/pi/files_nmap/ssid_noscan.txt
```

Example:

```text
Club_Totalplay_WiFi
Megacable Gratis
CASINO_HERMOSILLO
```

4. Create `ssid_known.json` (known networks and passwords):

```bash
sudo nano /home/pi/files_nmap/ssid_known.json
```

Example:

```text
Totalplay-CCCX PASSWORD123
MiRedCasa123 pa55w0rd
CafeteriaLibre 12345678
```

> Note: The current parser expects one network per line in the format `SSID PASSWORD`, even though the file is named `.json`.

5. Enable the plugins in `/etc/pwnagotchi/config.toml`:

```toml
main.plugins.auto_nmap.enabled = true
main.plugins.file_editor.enabled = true
```

6. Restart Pwnagotchi:

```bash
sudo systemctl restart pwnagotchi
```

---

## ⚙️ Configuration

### `auto_nmap.py` / `auto_nmap_noui.py`

Inside the script you can adjust:

```python
SSID_NOSCAN = ["SSID0", "SSID1", "SSID2"]
SSID_KNOWN = {
    "SSID": "PASSWORD",
}
```

The final version loads these from:

- `/home/pi/files_nmap/ssid_noscan.txt`
- `/home/pi/files_nmap/ssid_known.json`

### `file_editor.py`

Served directories:

```python
self.directories = {
    'files_nmap': '/home/pi/files_nmap',
    'auto_nmap': '/home/pi/auto_nmap',
    'handshakes': '/home/pi/handshakes'
}
```

Web server port: `9666`.

---

## 🛠️ Usage

Once enabled, the plugin works automatically:

1. Pwnagotchi detects available access points.
2. The plugin checks for known networks first.
3. If none match, it tries open networks (excluding `SSID_NOSCAN`).
4. It connects using `wpa_supplicant` and obtains an IP with `dhclient`.
5. It runs `nmap -T4 -F` on the local subnet.
6. The scan is saved to `/home/pi/auto_nmap/nmap_scan_<SSID>_<date>.log`.
7. It disconnects and waits for the next cycle.
8. The UI plugin shows status like `[~]:SSID`, `[O]:SSID`, or `[X]:SSID`.

### Web Interface

Access from any device on the same network:

```text
http://<pwnagotchi-ip>:9666
```

From there you can:

- Browse `files_nmap`, `auto_nmap`, and `handshakes`.
- Download individual files.
- Download a whole folder as ZIP.
- View text files.
- Edit text files and save changes.

---

## 🖼️ Screenshot

![Pwnagotchi Auto-Nmap](https://github.com/user-attachments/assets/e472cdf2-aae8-43ca-8a78-02b4fa6907a1)

---

## ⚠️ Warnings

- **Authorization:** Only scan networks you own or have explicit permission to test.
- **Legality:** Unauthorized network scanning and access is illegal in many countries.
- **Stability:** Connecting and disconnecting `wlan1` may interfere with Pwnagotchi’s normal operations.
- **Security:** The web interface has no authentication. Do not expose it to the public internet.
- **Responsibility:** The author is not responsible for misuse or damage caused by this software.

---

## 🤝 Contributing

Contributions are welcome.

1. Fork the repository.
2. Create a branch:
   ```bash
   git checkout -b feature/new-feature
   ```
3. Commit your changes:
   ```bash
   git commit -m "Add new feature"
   ```
4. Push the branch:
   ```bash
   git push origin feature/new-feature
   ```
5. Open a Pull Request.

---

## 📄 License

This project is released under the **GPL3** license, as indicated in the source files.

---

## 👤 Author

**akthanon**

- GitHub: [https://github.com/akthanon](https://github.com/akthanon)

Based on original work by **@jorge** and **@nagy_craig**.

---

**📡 Pwnagotchi Auto-Nmap — Automated Wi-Fi scanning and file access for Pwnagotchi.**
