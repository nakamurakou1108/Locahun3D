#!/usr/bin/env python3
"""
Capture a viewport screenshot from a Chrome instance launched with
`--remote-debugging-port=9222`. Foreground-independent — works even when
Chrome is minimized or covered.

Usage:
    python __cdp_shot.py output.png [tab_url_substring]
"""
import json, sys, base64, urllib.request, socket
from urllib.error import URLError

PORT = 9222
URL  = sys.argv[1] if len(sys.argv) > 1 else 'shot.png'
match = sys.argv[2] if len(sys.argv) > 2 else 'Locahun3D'

def http_json(path):
    with urllib.request.urlopen(f'http://127.0.0.1:{PORT}{path}', timeout=5) as r:
        return json.loads(r.read())

# Find the target tab
tabs = http_json('/json')
tab = next((t for t in tabs if t.get('type') == 'page' and match in (t.get('url','') + t.get('title',''))), None)
if not tab:
    print(f'no tab matching "{match}" found. tabs:', [t.get('url') for t in tabs])
    sys.exit(1)

# Minimal CDP over WebSocket
ws_url = tab['webSocketDebuggerUrl']
# Parse ws://host:port/devtools/page/<id>
from urllib.parse import urlparse
u = urlparse(ws_url)
host, port = u.hostname, u.port
path = u.path

# Manually speak the WebSocket protocol enough to send one CDP command + recv
import struct, os, base64 as b64

# WebSocket handshake
key = b64.b64encode(os.urandom(16)).decode()
sock = socket.create_connection((host, port), timeout=10)
sock.send((
    f'GET {path} HTTP/1.1\r\n'
    f'Host: {host}:{port}\r\n'
    'Upgrade: websocket\r\n'
    'Connection: Upgrade\r\n'
    f'Sec-WebSocket-Key: {key}\r\n'
    'Sec-WebSocket-Version: 13\r\n\r\n'
).encode())
# Drain handshake response
buf = b''
while b'\r\n\r\n' not in buf:
    buf += sock.recv(4096)
if b'101' not in buf.split(b'\r\n')[0]:
    print('WebSocket handshake failed:', buf[:200]); sys.exit(1)

def send_frame(payload):
    data = payload.encode()
    header = bytearray([0x81])  # FIN + text
    mask = os.urandom(4)
    if len(data) < 126:
        header.append(0x80 | len(data))
    elif len(data) < 65536:
        header.extend([0x80 | 126, *struct.pack('>H', len(data))])
    else:
        header.extend([0x80 | 127, *struct.pack('>Q', len(data))])
    header.extend(mask)
    masked = bytes(b ^ mask[i%4] for i, b in enumerate(data))
    sock.send(bytes(header) + masked)

def recv_frame():
    h = sock.recv(2)
    if not h or len(h) < 2: return None
    op = h[0] & 0x0F
    masked = h[1] & 0x80
    ln = h[1] & 0x7F
    if ln == 126:
        ln = struct.unpack('>H', sock.recv(2))[0]
    elif ln == 127:
        ln = struct.unpack('>Q', sock.recv(8))[0]
    if masked:
        mask = sock.recv(4)
    payload = b''
    while len(payload) < ln:
        chunk = sock.recv(ln - len(payload))
        if not chunk: break
        payload += chunk
    if masked:
        payload = bytes(b ^ mask[i%4] for i, b in enumerate(payload))
    return op, payload

# Send Page.captureScreenshot
cmd = json.dumps({'id': 1, 'method': 'Page.captureScreenshot', 'params': {'format':'png','captureBeyondViewport':False}})
send_frame(cmd)

# Read frames until we see the response with id:1
while True:
    f = recv_frame()
    if f is None: print('connection closed'); sys.exit(1)
    op, payload = f
    if op == 0x1:  # text
        try:
            msg = json.loads(payload.decode('utf-8'))
        except Exception:
            continue
        if msg.get('id') == 1:
            if 'error' in msg:
                print('CDP error:', msg['error']); sys.exit(1)
            data_b64 = msg['result']['data']
            with open(URL, 'wb') as f:
                f.write(b64.b64decode(data_b64))
            print(f'saved {URL} ({os.path.getsize(URL)} bytes)')
            sys.exit(0)
