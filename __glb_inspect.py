#!/usr/bin/env python3
"""Parse a GLB file's JSON header (no deps) to learn its structure."""
import json, sys, struct
from pathlib import Path

path = Path(sys.argv[1])
with path.open('rb') as f:
    magic, version, total = struct.unpack('<4sII', f.read(12))
    assert magic == b'glTF', f'not a GLB (magic={magic})'
    chunk_len, chunk_type = struct.unpack('<I4s', f.read(8))
    assert chunk_type == b'JSON', f'expected JSON chunk, got {chunk_type}'
    j = json.loads(f.read(chunk_len).decode('utf-8'))

print(f'═══ {path.name}  ({path.stat().st_size:,} bytes, glTF v{version}) ═══\n')

print('asset:', j.get('asset', {}))
print(f'scenes: {len(j.get("scenes", []))}')
print(f'nodes:  {len(j.get("nodes", []))}')
print(f'meshes: {len(j.get("meshes", []))}')
print(f'skins:  {len(j.get("skins", []))}')
print(f'animations: {len(j.get("animations", []))}')

print('\n── Animations ──')
for i, a in enumerate(j.get('animations', [])):
    name = a.get('name', f'(unnamed #{i})')
    chans = len(a.get('channels', []))
    samplers = len(a.get('samplers', []))
    print(f'  [{i}] "{name}"  channels={chans}  samplers={samplers}')

print('\n── Skins / Bone names (first 30) ──')
nodes = j.get('nodes', [])
for s_idx, s in enumerate(j.get('skins', [])):
    joints = s.get('joints', [])
    print(f'  skin[{s_idx}] joints={len(joints)}')
    for ji, ni in enumerate(joints[:30]):
        name = nodes[ni].get('name', f'(unnamed #{ni})')
        print(f'    [{ji}] node#{ni}  "{name}"')
    if len(joints) > 30: print(f'    ... +{len(joints)-30} more joints')

print('\n── Root scene tree (first level) ──')
for s in j.get('scenes', []):
    for ni in s.get('nodes', []):
        n = nodes[ni]
        print(f'  root node "{n.get("name","?")}"  mesh={n.get("mesh")}  skin={n.get("skin")}  children={len(n.get("children",[]))}')
