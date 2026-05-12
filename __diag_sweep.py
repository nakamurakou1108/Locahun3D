#!/usr/bin/env python3
"""Extract render-cost stats from the current __diag.log (single quality run)."""
import json, statistics, sys
from pathlib import Path

LOG = Path(__file__).parent / '__diag.log'
snaps = []
with LOG.open(encoding='utf-8') as f:
    for line in f:
        try:
            ts, body = line.strip().split(' ', 1)
            d = json.loads(body)
        except Exception:
            continue
        if 'entries' not in d: continue
        for e in d['entries']:
            if e.get('ev') == 'snap':
                snaps.append(e)

if not snaps:
    print('no snaps yet'); sys.exit()

# Discard first 8 s of warmup
t0 = snaps[0]['t']
steady = [s for s in snaps if s['t'] - t0 > 8000 and isinstance(s.get('ftAvg'), (int,float))]
ft = [s['ftAvg'] for s in steady]
wm = [s['wallMs'] for s in steady]
q  = [s['q'] for s in steady]
pr = [s['pr'] for s in steady]

print(f'snaps total={len(snaps)} steady={len(steady)}')
print(f'qualScale (last 5): {q[-5:]}')
print(f'pixelRatio (last 5): {pr[-5:]}')
if ft:
    print(f'_ftAvg (with gl.finish if enabled):')
    print(f'  min={min(ft):6.2f}  p50={statistics.median(ft):6.2f}  '
          f'p95={sorted(ft)[int(len(ft)*0.95)]:6.2f}  max={max(ft):6.2f}')
if wm:
    print(f'_wallMsAvg:')
    print(f'  min={min(wm):6.2f}  p50={statistics.median(wm):6.2f}  '
          f'p95={sorted(wm)[int(len(wm)*0.95)]:6.2f}  max={max(wm):6.2f}')
print(f'\nfps from wall: {round(1000/statistics.median(wm),1) if wm else "?"}')
print(f'gpu/wall ratio: {round(statistics.median(ft)/statistics.median(wm)*100,1) if wm and ft else "?"} %  (high → GPU-bound, low → vsync/CPU-bound)')
