# Advanced QR File Transfer (Python)

A local‐network file‐sharing utility that serves files or directories over HTTP and prints a QR code in your terminal for instant mobile downloads. This Python reimplementation of the Go-based `qr-filetransfer` tool adds powerful new capabilities:

- **Password protection** (via URL param or HTTP header)  
- **Link expiration** (auto-expire after a given number of seconds)  
- **Download counting** (track how many times each token URL was used)  
- **Persistent interface config** (remembers your last `-i` setting)  
- **Automatic zipping** of folders or multiple files  
- **Secure, random tokens** for unguessable URLs  

---  

## Table of Contents

1. [Installation](#installation)  
2. [Quick Start](#quick-start)  
3. [Command-Line Options](#command-line-options)  
4. [How It Works](#how-it-works)  
5. [Security & Privacy](#security--privacy)  
6. [Example Scenarios](#example-scenarios)  
7. [Troubleshooting](#troubleshooting)  
8. [Development & Internals](#development--internals)  


---

## Installation

1. **Clone the repository**  
   ```bash
   git clone https://github.com/rkstudio585/qr-filetransfer.git
   cd qr-filetransfer
  ```
2. Install dependencies
```bash
apt install uv -y
uv pip3 install -r requirements.txt
```

3. Make the script executable (optional)
```bash
chmod +x qrtransfer.py
```


---

## Quick Start

Serve a single file, no password, never expires:
```bash
./qrtransfer.py myphoto.jpg
```
OR

```bash
python qrtransfer.py -h
```
You’ll see:

A QR code representing `http://<your-ip>:<port>/<token>`

The same URL printed in plain text


Scan that QR with your phone’s camera or QR app, and the file downloads immediately.


---

## Command-Line Options

Option	Description

paths	One or more files or directories to serve
`-z`,`--zip`	Zip up multiple files or entire directory before serving
`-i`, `--interface INTERFACE` Network interface (e.g. eth0, wlan0) to bind to and remember for next time
`-e`,`--expire SECONDS`	Automatically expire the link after N seconds (0 = never)
`-p`,`--password SECRET`	Protect download with a password—passed either as URL param ?passed=SECRET or HTTP header X-Password
`-h`,`--help`	Show help text and exit



---

## How It Works

1. Token Generation
On start, the script generates a random URL token (e.g. f9aX23_q).


2. Zipping (if needed)
If you pass `--zip` or more than one path, it creates a temporary .zip archive.


3. HTTP Server
It launches a lightweight, threaded HTTP server on a free port, binding to your chosen interface (or auto-detecting).


4. QR Code & URL
Prints an ASCII QR code of the full download URL (including ?passed=... if passworded) plus the URL itself.


5. Request Handling

Checks for token match in path

Validates password (URL param or X-Password header)

Enforces expiration time if set

Increments an in-memory download counter

Serves the file or returns an HTTP error (401, 404, 410)



6. Shutdown & Cleanup
Press Enter (or Ctrl+C) to stop. If a zip archive was created, it’s deleted. The script then prints the total download count.




---

## Security & Privacy

Local-only: No data leaves your LAN unless you deliberately port-forward.

Unpredictable tokens: Uses Python’s secrets module for cryptographic randomness.

Password options: You can embed the secret in the QR URL or require an HTTP header for extra stealth.

Expiration: Even if someone saves the QR, it won't work after the expiry window.

No logs on disk: Download counts and config are kept in memory or a tiny JSON file under ~/.qr-filetransfer.json.



---

## Example Scenarios

1. Quickly share a photo with a friend
```bash
./qrtransfer.py -i wlan0 --expire 300 holiday.jpg
```
— Expires in 5 minutes. Friend scans and downloads over Wi-Fi.


2. Distribute a small app build within your team
```bash
./qrtransfer.py --zip builds/ --password teamSecret123
```
— QR URL includes `?passed=teamSecret123`. Easy for teammates, locked to outsiders.


3. Share multiple docs securely
```bash
./qrtransfer.py docs/*.pdf
```
— Automatically zips, no password, no expiry.



---

### Troubleshooting

“Address already in use”: Another server is running on that interface; try a different interface or kill the process.

No QR code in terminal: Ensure your font is monospaced and that qrcode-terminal is installed.

Cannot detect interface IP: Provide -i <iface> explicitly; check ifconfig or ip addr.



---

## Development & Internals

Language & Modules

Core: Python 3’s `http.server`, `socket`, `threading`

Zip: `zipfile`, `tempfile`

QR: `qrcode_terminal`

Networking: `netifaces` for interface lookups


## Extending

Add TLS support by wrapping the server socket with ssl

Persist download counts to disk or integrate a small database

Build a simple web UI instead of terminal QR code

---
