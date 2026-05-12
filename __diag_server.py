#!/usr/bin/env python3
"""
Diagnostic collector for Locahun3D flicker investigation.

Serves the project directory at / (so the viewer can be loaded), and accepts
POST /__diag with JSON bodies. Each POST is appended as a line to __diag.log.

Run:
    python __diag_server.py
Then open:
    http://localhost:8765/Locahun3D_OfflineViewer.html
"""
import http.server
import json
import os
import socketserver
import sys
import time
from datetime import datetime

PORT = 8765
LOG_FILE = '__diag.log'

# Allow writes from the page
class DiagHandler(http.server.SimpleHTTPRequestHandler):
    def end_headers(self):
        # Be permissive for local diagnostics
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Methods', 'GET, POST, OPTIONS')
        self.send_header('Access-Control-Allow-Headers', 'Content-Type')
        # No cache so HTML edits are picked up on reload
        if self.path.endswith('.html') or self.path == '/':
            self.send_header('Cache-Control', 'no-cache, no-store, must-revalidate')
        super().end_headers()

    def do_OPTIONS(self):
        self.send_response(204)
        self.end_headers()

    def do_POST(self):
        if self.path != '/__diag':
            self.send_response(404); self.end_headers(); return
        try:
            n = int(self.headers.get('Content-Length','0'))
            body = self.rfile.read(n).decode('utf-8', errors='replace')
        except Exception as e:
            self.send_response(400); self.end_headers()
            self.wfile.write(str(e).encode()); return
        ts = datetime.now().isoformat(timespec='milliseconds')
        with open(LOG_FILE, 'a', encoding='utf-8') as f:
            f.write(f'{ts} {body}\n')
        self.send_response(204); self.end_headers()

    def log_message(self, fmt, *args):
        # Quiet — we have our own log
        if '/__diag' in (args[0] if args else ''):
            return
        sys.stderr.write(f'[{datetime.now().strftime("%H:%M:%S")}] {fmt % args}\n')

if __name__ == '__main__':
    os.chdir(os.path.dirname(os.path.abspath(__file__)))
    # Truncate log on each run
    open(LOG_FILE, 'w').close()
    with socketserver.ThreadingTCPServer(('127.0.0.1', PORT), DiagHandler) as httpd:
        print(f'Diag server: http://127.0.0.1:{PORT}/   (log → {LOG_FILE})')
        httpd.serve_forever()
