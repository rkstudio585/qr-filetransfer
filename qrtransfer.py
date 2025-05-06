#!/usr/bin/env python3
import argparse
import json
import os
import socket
import sys
import tempfile
import threading
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
import zipfile
import secrets
import time
from urllib.parse import urlparse, parse_qs

try:
    import qrcode_terminal
    import netifaces
except ImportError:
    print("Missing dependencies. Please run 'pip install -r requirements.txt'.")
    sys.exit(1)

CONFIG_PATH = Path.home() / '.qr-filetransfer.json'
DOWNLOAD_COUNTER = {}
TOKEN = secrets.token_urlsafe(8)


def load_config():
    if CONFIG_PATH.exists():
        try:
            return json.loads(CONFIG_PATH.read_text())
        except json.JSONDecodeError:
            pass
    return {}


def save_config(interface: str):
    CONFIG_PATH.write_text(json.dumps({'interface': interface}))


def get_ip(interface: str = None) -> str:
    if interface:
        addrs = netifaces.ifaddresses(interface)
        inet = addrs.get(netifaces.AF_INET)
        if inet:
            return inet[0]['addr']
        raise ValueError(f"Interface '{interface}' not found or has no IPv4 address.")
    with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as s:
        s.connect(('8.8.8.8', 80))
        return s.getsockname()[0]


def find_free_port() -> int:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind(('', 0))
        return s.getsockname()[1]


def zip_content(paths: list[str]) -> tuple[str, bool]:
    tmp = tempfile.NamedTemporaryFile(delete=False, suffix='.zip')
    zip_path = tmp.name
    tmp.close()
    with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED) as zf:
        for p in paths:
            p = Path(p)
            if p.is_dir():
                for file in p.rglob('*'):
                    zf.write(file, file.relative_to(p.parent))
            else:
                zf.write(p, p.name)
    return zip_path, True


def serve_file(file_path: str, port: int, expire: int, password: str = None):
    directory = os.path.dirname(file_path) or '.'
    os.chdir(directory)
    filename = os.path.basename(file_path)
    expiry_time = time.time() + expire if expire > 0 else None

    class Handler(SimpleHTTPRequestHandler):
        def do_GET(self):
            # Expiration
            if expiry_time and time.time() > expiry_time:
                self.send_error(410, "Link expired")
                return
            # Token & param
            parsed = urlparse(self.path)
            path_token = parsed.path.lstrip('/')
            query = parse_qs(parsed.query)
            # Password check
            if password:
                valid = False
                # Check URL param
                if query.get('passed', [None])[0] == password:
                    valid = True
                # Check header fallback
                elif self.headers.get('X-Password') == password:
                    valid = True
                if not valid:
                    self.send_error(401, "Unauthorized. Provide password via '?passed=SECRET' or header X-Password.")
                    return
            # Token validation and serve
            if path_token == TOKEN:
                DOWNLOAD_COUNTER[TOKEN] = DOWNLOAD_COUNTER.get(TOKEN, 0) + 1
                self.path = f'/{filename}'
                return super().do_GET()
            self.send_error(404)

    server = ThreadingHTTPServer(('0.0.0.0', port), Handler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    return server


def main():
    parser = argparse.ArgumentParser(description='Advanced QR File Transfer')
    parser.add_argument('paths', nargs='+', help='Files or directories to transfer')
    parser.add_argument('--zip', action='store_true', help='Zip contents before transfer')
    parser.add_argument('-i', '--interface', help='Network interface to use')
    parser.add_argument('--expire', type=int, default=0, help='Time in seconds before link expires (0 = never)')
    parser.add_argument('--password', help="Password required to download (via URL param 'passed' or HTTP header X-Password)")
    args = parser.parse_args()

    config = load_config()
    interface = args.interface or config.get('interface')
    if args.interface:
        save_config(args.interface)

    # Prepare file
    paths = args.paths
    if args.zip or len(paths) > 1:
        file_path, should_delete = zip_content(paths)
    else:
        file_path = paths[0]
        should_delete = False

    # Determine IP & port
    try:
        ip = get_ip(interface)
    except Exception as e:
        print(f"Error determining IP: {e}")
        sys.exit(1)
    port = find_free_port()

    # Build URL
    base_url = f'http://{ip}:{port}/{TOKEN}'
    if args.password:
        url = f"{base_url}?passed={args.password}"
    else:
        url = base_url

    # Display
    print('Scan this QR code to download:')
    qrcode_terminal.draw(url)
    print(f'URL: {url}')
    if args.password:
        print("[Protected] Password is in URL param 'passed' or HTTP header X-Password.")
    if args.expire:
        print(f"[Notice] Link will expire in {args.expire} seconds")

    server = serve_file(file_path, port, args.expire, args.password)
    try:
        input('Press Enter or Ctrl+C to stop transfer...')
    except KeyboardInterrupt:
        pass
    server.shutdown()
    if should_delete:
        os.remove(file_path)
    print('Transfer session ended.')
    print(f"Total downloads: {DOWNLOAD_COUNTER.get(TOKEN, 0)}")


if __name__ == '__main__':
    main()
