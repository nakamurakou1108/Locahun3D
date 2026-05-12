#!/usr/bin/env python3
"""Extract the splatMeshDump record and the renderer.info trajectory."""
import json, sys
from pathlib import Path
from collections import Counter

LOG = Path(__file__).parent / '__diag.log'

dump = None
calls = []
geoms = []
txs = []
prog = []

with LOG.open(encoding='utf-8') as f:
    for line in f:
        line = line.strip()
        if not line: continue
        try:
            iso, body = line.split(' ', 1)
            d = json.loads(body)
        except Exception:
            continue
        if d.get('ev') == 'splatMeshDump':
            dump = d
        if 'entries' in d:
            for e in d['entries']:
                if e.get('ev') != 'snap': continue
                if 'calls' in e:
                    calls.append(e['calls'])
                    geoms.append(e['geoms'])
                    txs.append(e['txs'])
                    prog.append(e['progr'])

if dump:
    print('═'*60); print('SplatMesh property dump'); print('═'*60)
    print(f'sm key count: {len(dump["dump"]["sm_keys"])}')
    print(f'sm LOD-related properties:')
    for k, v in sorted(dump['dump']['sm_lod_related'].items()):
        sv = json.dumps(v) if not isinstance(v, str) else v
        if len(sv) > 80: sv = sv[:80]+'...'
        print(f'   {k:30s} = {sv}')
    print(f'\npackedSplats key count: {len(dump["dump"]["ps_keys"])}')
    print(f'packedSplats LOD-related properties:')
    for k, v in sorted(dump['dump']['ps_lod_related'].items()):
        sv = json.dumps(v) if not isinstance(v, str) else v
        if len(sv) > 80: sv = sv[:80]+'...'
        print(f'   {k:30s} = {sv}')
else:
    print('No splatMeshDump record yet.')

print('\n' + '═'*60); print('renderer.info trajectory'); print('═'*60)
def stats(name, arr):
    if not arr: print(f'  {name}: no data'); return
    print(f'  {name}: min={min(arr)} max={max(arr)} unique={sorted(set(arr))[:5]}{"..." if len(set(arr))>5 else ""}')
stats('calls (draw)', calls)
stats('geoms      ', geoms)
stats('textures   ', txs)
stats('programs   ', prog)
