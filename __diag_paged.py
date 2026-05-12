#!/usr/bin/env python3
"""Compare paged-on vs paged-off load behavior."""
import json, sys
from pathlib import Path
LOG = Path(sys.argv[1] if len(sys.argv) > 1 else __file__).parent / '__diag.log'
if len(sys.argv) > 1:
    LOG = Path(sys.argv[1])

snaps = []
rafs = []
with LOG.open(encoding='utf-8') as f:
    for line in f:
        try:
            _, body = line.strip().split(' ', 1)
            d = json.loads(body)
        except Exception:
            continue
        if d.get('ev') == 'rafProbe':
            rafs.append(d)
        if 'entries' in d:
            for e in d['entries']:
                if e.get('ev') == 'snap':
                    snaps.append(e)

# Splat count timeline
print('═══ numSplats over time (s after first sample) ═══')
if snaps:
    t0 = snaps[0]['t']
    seen = set()
    first_nonzero_t = None
    last_count = 0
    for s in snaps:
        n = s.get('numSplats')
        if n is None: continue
        if n != last_count or s is snaps[-1]:
            dt = (s['t']-t0)/1000
            print(f'  +{dt:6.1f}s  numSplats={n:>10,}  (q={s.get("q")} pr={s.get("pr")} fps={s.get("fps")})')
            last_count = n
            if first_nonzero_t is None and n > 0:
                first_nonzero_t = dt
                print(f'    ↑ FIRST SPLATS RENDERED at +{dt:.1f}s')

# rAF timeline
print('\n═══ rAF cadence (probe, every ~0.4s) ═══')
prev = None
for r in rafs:
    bucket = int(r['sinceStartMs']/1000)
    if prev != bucket:
        flag = '  ★' if r['fps'] > 100 else ('  ↓' if r['fps'] < 60 else '')
        print(f'  +{r["sinceStartMs"]/1000:6.1f}s  rAF={r["fps"]:6.1f} fps{flag}')
        prev = bucket
