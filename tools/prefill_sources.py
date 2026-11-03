"""Where does the prompt reading (uncached prompt tokens) come from? Player requests only (requests logs), per run:
uncached = prompt_tokens - cached_tokens per request; bucketed into normal turns vs large re-reads (history trims,
cache misses), with image tokens and their share. usage: python -I prefill_sources.py <project_dir> run [run ...]"""
import glob
import json
import os
import statistics as st
import sys

sys.stdout.reconfigure(encoding='utf-8')
ROOT = sys.argv[1]
for run in sys.argv[2:]:
    unc = []
    imgs = []
    prompt_total = cached_total = gen_total = 0
    for rq in sorted(glob.glob(os.path.join(ROOT, f'results_{run}', '*_p0_requests.jsonl'))):
        for line in open(rq, encoding='utf-8'):
            if '"event": "response"' not in line[-3000:]:
                continue
            r = json.loads(line)
            u = r.get('usage') or {}
            p = int(u.get('prompt_tokens') or 0)
            d = u.get('prompt_tokens_details') or {}
            c = int(d.get('cached_tokens') or 0)
            im = int(((d.get('multimodal_tokens') or {}).get('image')) or 0)
            prompt_total += p
            cached_total += c
            gen_total += int(u.get('completion_tokens') or 0)
            unc.append(max(0, p - c))
            imgs.append(im)
    if not unc:
        print(run, 'no responses')
        continue
    tot = sum(unc)
    big = [x for x in unc if x >= 20000]
    mid = [x for x in unc if 5000 <= x < 20000]
    small = [x for x in unc if x < 5000]
    print(f"{run}: {len(unc)} player requests | prompt {prompt_total / 1e6:.1f}M, cached {100 * cached_total / prompt_total:.1f}% -> "
          f"read {tot / 1e6:.2f}M uncached tokens = {tot / gen_total:.2f} per generated token")
    print(f"   normal turns (<5K): {len(small)} req, {100 * sum(small) / tot:.0f}% of reading, median {st.median(small):.0f} tok | "
          f"5-20K: {len(mid)} req, {100 * sum(mid) / tot:.0f}% | re-reads >=20K: {len(big)} req, {100 * sum(big) / tot:.0f}% "
          f"(median {st.median(big) if big else 0:.0f} tok)")
    print(f"   image tokens per request: median {st.median(imgs):.0f} (these are in the prompt; cached when unchanged)")
