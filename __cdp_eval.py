#!/usr/bin/env python3
"""Execute JS in the Chrome page via CDP and return result."""
import json, sys, socket, struct, os, base64 as b64, urllib.request
from urllib.parse import urlparse

PORT = 9222
js_expr = sys.argv[1]

tabs = json.loads(urllib.request.urlopen(f'http://127.0.0.1:{PORT}/json', timeout=5).read())
tab = next((t for t in tabs if t.get('type')=='page' and 'Locahun3D' in (t.get('url','')+t.get('title',''))), None)
if not tab: print('no tab'); sys.exit(1)
u = urlparse(tab['webSocketDebuggerUrl'])
sock = socket.create_connection((u.hostname, u.port), timeout=30)
sock.settimeout(30)
key = b64.b64encode(os.urandom(16)).decode()
sock.send((f'GET {u.path} HTTP/1.1\r\nHost: {u.hostname}:{u.port}\r\nUpgrade: websocket\r\nConnection: Upgrade\r\nSec-WebSocket-Key: {key}\r\nSec-WebSocket-Version: 13\r\n\r\n').encode())
buf = b''
while b'\r\n\r\n' not in buf: buf += sock.recv(4096)

def send(p):
    d = p.encode(); h = bytearray([0x81]); m = os.urandom(4)
    if len(d) < 126: h.append(0x80|len(d))
    elif len(d) < 65536: h.extend([0x80|126, *struct.pack('>H',len(d))])
    else: h.extend([0x80|127, *struct.pack('>Q',len(d))])
    h.extend(m)
    sock.send(bytes(h) + bytes(b ^ m[i%4] for i,b in enumerate(d)))

def recv():
    h = sock.recv(2)
    if not h or len(h)<2: return None
    op = h[0]&0x0F; ln = h[1]&0x7F
    if ln==126: ln = struct.unpack('>H', sock.recv(2))[0]
    elif ln==127: ln = struct.unpack('>Q', sock.recv(8))[0]
    p = b''
    while len(p) < ln: c = sock.recv(ln-len(p)); p += c if c else b''
    return op, p

# Bring page to front BEFORE evaluating so Chrome marks it visible
send(json.dumps({'id':0, 'method':'Page.bringToFront'}))
# drain Page.bringToFront response
for _ in range(5):
    f = recv()
    if not f: break
    try:
        m = json.loads(f[1].decode())
        if m.get('id') == 0: break
    except: pass
send(json.dumps({'id':1, 'method':'Runtime.evaluate', 'params':{'expression': js_expr, 'returnByValue': True, 'awaitPromise': True}}))
while True:
    f = recv()
    if not f: print('closed'); sys.exit(1)
    op, p = f
    if op != 1: continue
    try: msg = json.loads(p.decode())
    except: continue
    if msg.get('id') == 1:
        r = msg.get('result', {})
        if 'exceptionDetails' in r: print('JS ERROR:', r['exceptionDetails'].get('text','?')); sys.exit(1)
        val = r.get('result', {}).get('value')
        print(json.dumps(val, indent=2))
        sys.exit(0)
