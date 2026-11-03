"""Is the model's previous reply re-read on the next request? For consecutive (reply i, request i+1) pairs of the same
game in the requests logs: x = completion tokens of reply i, y = uncached prompt tokens of request i+1 (prompt -
cached). Fit y = c + d x on pairs whose next request did not trim (y < 20K). d ~ 1 -> the reply is read again in full;
d ~ 0 -> it is reused from the cache. usage: python -I reply_reread.py <project_dir> run [run ...]"""
import glob
import json
import os
import statistics as st
import sys

sys.stdout.reconfigure(encoding='utf-8')
ROOT = sys.argv[1]
for run in sys.argv[2:]:
    pairs = []
    for rq in sorted(glob.glob(os.path.join(ROOT, f'results_{run}', '*_p0_requests.jsonl'))):
        prev_completion = None
        for line in open(rq, encoding='utf-8'):
            tail = line[-3000:]
            if '"event": "response"' not in tail:
                continue
            r = json.loads(line)
            u = r.get('usage') or {}
            unc = int(u.get('prompt_tokens') or 0) - int((u.get('prompt_tokens_details') or {}).get('cached_tokens') or 0)
            if prev_completion is not None and unc < 20000:
                pairs.append((prev_completion, unc))
            prev_completion = int(u.get('completion_tokens') or 0)
    xs, ys = [p[0] for p in pairs], [p[1] for p in pairs]
    mx, my = st.mean(xs), st.mean(ys)
    d = sum((x - mx) * (y - my) for x, y in pairs) / sum((x - mx) ** 2 for x in xs)
    c = my - d * mx
    print(f"{run}: {len(pairs)} pairs | mean reply {mx:.0f} tok, mean next re-read {my:.0f} tok | fit re-read = {c:.0f} + "
          f"{d:.2f} x previous reply")
    for lo, hi in ((0, 1000), (1000, 3000), (3000, 6000), (6000, 13000)):
        sel = [y for x, y in pairs if lo <= x < hi]
        if sel:
            print(f"   previous reply {lo}-{hi}: next request re-read median {st.median(sel):.0f} tok (n={len(sel)})")
