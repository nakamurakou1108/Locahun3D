#!/usr/bin/env python3
"""Analyze the Locahun3D flicker diagnostic log."""
import json, sys, statistics
from collections import Counter, defaultdict
from pathlib import Path

LOG = Path(__file__).parent / '__diag.log'

snaps, prChanges, qualChanges, shResets, lodReassert, foveateAlerts = [], [], [], [], [], []
post_count = 0
first_ts = None

with LOG.open(encoding='utf-8') as f:
    for line in f:
        line = line.strip()
        if not line:
            continue
        try:
            iso, body = line.split(' ', 1)
            d = json.loads(body)
        except Exception:
            continue
        if 'entries' not in d:
            continue  # smoke-test rows
        post_count += 1
        if first_ts is None:
            first_ts = iso
        for e in d['entries']:
            ev = e.get('ev')
            if ev == 'snap':
                snaps.append(e)
            elif ev == 'setPR':
                prChanges.append(e)
            elif ev == 'qualChange':
                qualChanges.append(e)
            elif ev == 'shReset':
                shResets.append(e)
            elif ev == 'lodReassert':
                lodReassert.append(e)
            elif ev == 'foveateAlert':
                foveateAlerts.append(e)

if not snaps:
    print('No snapshot data yet.')
    sys.exit(0)

print(f'═══ Locahun3D flicker diagnostic ═══')
print(f'POSTs: {post_count}  | first_ts: {first_ts}')
print(f'Snapshots: {len(snaps)}  | duration: {(snaps[-1]["t"]-snaps[0]["t"])/1000:.1f}s')
print()

# ─ Quality timeline ─
q_vals = [s['q'] for s in snaps if s.get('q') is not None]
pr_vals = [s['pr'] for s in snaps if s.get('pr') is not None]
print(f'qualScale unique values seen: {sorted(set(q_vals))}')
print(f'pixelRatio unique values seen: {sorted(set(pr_vals))}')

print(f'\n── setPixelRatio call count: {len(prChanges)}')
for c in prChanges[:25]:
    print(f'  +{c["t"]/1000:7.1f}s pr={c["pr"]} caller={c.get("caller","")[:140]}')
if len(prChanges) > 25:
    print(f'  ... and {len(prChanges)-25} more')

print(f'\n── qualScale transitions: {len(qualChanges)}')
for c in qualChanges:
    print(f'  +{c["t"]/1000:7.1f}s  {c.get("from")} → {c.get("to")}')

print(f'\n── SH resets (numShU < maxSh) per-snap: {len(shResets)}')
if shResets[:10]:
    for r in shResets[:10]:
        print(f'  +{r["t"]/1000:7.1f}s  u={r["u"]} max={r["max"]}')

print(f'\n── LOD re-assertion events (sm.enableLod was true): {len(lodReassert)}')
print(f'── Foveation alert events (coneFoveate > 0):       {len(foveateAlerts)}')

# ─ Frame-time distribution ─
ft = [s['ftAvg'] for s in snaps if isinstance(s.get('ftAvg'), (int, float)) and s['ftAvg'] > 0]
wm = [s['wallMs'] for s in snaps if isinstance(s.get('wallMs'), (int, float)) and s['wallMs'] > 0]
if ft:
    print(f'\n── Frame time (_ftAvg):')
    print(f'   min={min(ft):.1f}  p50={statistics.median(ft):.1f}  p95={sorted(ft)[int(len(ft)*0.95)]:.1f}  max={max(ft):.1f}')
if wm:
    print(f'── Wall ms (_wallMsAvg):')
    print(f'   min={min(wm):.1f}  p50={statistics.median(wm):.1f}  p95={sorted(wm)[int(len(wm)*0.95)]:.1f}  max={max(wm):.1f}')

# ─ Watchdog streaks ─
slow = [s.get('slowStreak',0) for s in snaps]
fast = [s.get('fastStreak',0) for s in snaps]
print(f'\n── Watchdog streaks: slow max={max(slow)} fast max={max(fast)}')

# ─ Coarse timeline (per-30s averages) ─
print(f'\n── Timeline (30s buckets) ──')
print(f'{"t(s)":>7} {"q":>5} {"pr":>5} {"ftAvg":>6} {"wallMs":>7} {"fps":>4} {"slow":>5} {"fast":>5}')
bucket_size = 30
buckets = defaultdict(list)
t0 = snaps[0]['t']
for s in snaps:
    bucket = int((s['t']-t0)/(bucket_size*1000))
    buckets[bucket].append(s)
for b, ss in sorted(buckets.items()):
    avg = lambda k: statistics.mean([x[k] for x in ss if isinstance(x.get(k),(int,float))]) if any(isinstance(x.get(k),(int,float)) for x in ss) else float('nan')
    print(f'{b*bucket_size:>6}s {avg("q"):>5.2f} {avg("pr"):>5.2f} {avg("ftAvg"):>6.1f} {avg("wallMs"):>7.1f} {avg("fps"):>4.0f} {avg("slowStreak"):>5.0f} {avg("fastStreak"):>5.0f}')

# ─ Spark internal state stability ─
e_lod_vals = Counter(s.get('enableLod') for s in snaps)
cf_vals = Counter(s.get('coneFoveate') for s in snaps)
shu_vals = Counter(s.get('numShU') for s in snaps)
print(f'\n── Spark state distribution ──')
print(f'enableLod values seen:    {dict(e_lod_vals)}')
print(f'coneFoveate values seen:  {dict(cf_vals)}')
print(f'numShU values seen:       {dict(shu_vals)}')
