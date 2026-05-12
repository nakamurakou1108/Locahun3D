#!/usr/bin/env python3
"""Show per-section CPU profiler results from the diag log."""
import json, statistics, sys
from pathlib import Path

LOG = Path(__file__).parent / '__diag.log'
profs = []
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
            if e.get('ev') == 'prof' and e.get('frames', 0) > 5:
                profs.append(e)
            elif e.get('ev') == 'snap':
                snaps.append(e)

if not profs:
    print('no prof entries yet'); sys.exit()

t0 = profs[0]['t']
steady = [p for p in profs if p['t'] - t0 > 8000]
print(f'prof entries total={len(profs)} steady={len(steady)}')
if steady:
    def s(arr, k):
        vs = sorted(arr)
        return (vs[0], statistics.median(vs), vs[int(len(vs)*0.95)], vs[-1])
    pre = [p['preRenderAvg'] for p in steady]
    ren = [p['renderAvg']    for p in steady]
    gap = [p['gapAvg']       for p in steady]
    frm = [p['frames']       for p in steady]
    print(f'per-frame avg ms (across 1s buckets):')
    print(f'  preRender (lerp/cam/halos/sort-hint)   min={min(pre):.2f} p50={statistics.median(pre):.2f} p95={sorted(pre)[int(len(pre)*0.95)]:.2f} max={max(pre):.2f}')
    print(f'  render+gl.finish (TRUE GPU time)       min={min(ren):.2f} p50={statistics.median(ren):.2f} p95={sorted(ren)[int(len(ren)*0.95)]:.2f} max={max(ren):.2f}')
    print(f'  gap (rAF-to-rAF, browser-vsync wait)   min={min(gap):.2f} p50={statistics.median(gap):.2f} p95={sorted(gap)[int(len(gap)*0.95)]:.2f} max={max(gap):.2f}')
    print(f'  frames/sec recorded                    min={min(frm)} p50={int(statistics.median(frm))} max={max(frm)}')
    tot = statistics.median(pre) + statistics.median(ren) + statistics.median(gap)
    print(f'\ntotal accounted = {tot:.2f} ms = {1000/tot:.1f} fps (matches wallMs/fps?)')
    print(f'\nbreakdown of per-frame budget:')
    pct = lambda x: f'{100*x/tot:.1f}%' if tot else '?'
    print(f'  preRender = {pct(statistics.median(pre))}')
    print(f'  render    = {pct(statistics.median(ren))}')
    print(f'  gap       = {pct(statistics.median(gap))}')
