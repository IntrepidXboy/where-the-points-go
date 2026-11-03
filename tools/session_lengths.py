"""Seat-session lengths (generated tokens between history trims) from the requests logs: a request whose uncached prompt
is >= 20K tokens is a trim (re-read); sessions = completion tokens between consecutive trims; first = until the first
trim. Also prompt growth per turn (new content + reply) between trims. usage: python -I session_lengths.py <project_dir> run"""
import glob
import json
import os
import statistics as st
import sys

sys.stdout.reconfigure(encoding='utf-8')
ROOT, run = sys.argv[1], sys.argv[2]
first, later, growth, kept = [], [], [], []
for rq in sorted(glob.glob(os.path.join(ROOT, f'results_{run}', '*_p0_requests.jsonl'))):
    gen_since, seen_trim, prev_prompt = 0, False, None
    for line in open(rq, encoding='utf-8'):
        if '"event": "response"' not in line[-3000:]:
            continue
        u = json.loads(line).get('usage') or {}
        p = int(u.get('prompt_tokens') or 0)
        c = int((u.get('prompt_tokens_details') or {}).get('cached_tokens') or 0)
        if p - c >= 20000:                      # this request re-read after a trim
            (later if seen_trim else first).append(gen_since)
            seen_trim, gen_since = True, 0
            kept.append(p)
        elif prev_prompt is not None and p > prev_prompt:
            growth.append(p - prev_prompt)
        gen_since += int(u.get('completion_tokens') or 0)
        prev_prompt = p
print(f"{run}: first session (to the first trim) median {st.median(first) / 1e3:.0f}K generated (n={len(first)}); later sessions "
      f"median {st.median(later) / 1e3:.0f}K, mean {st.mean(later) / 1e3:.0f}K (n={len(later)})")
print(f"   prompt right after a trim: median {st.median(kept) / 1e3:.0f}K | prompt growth per turn: median {st.median(growth):.0f}, "
      f"mean {st.mean(growth):.0f} tokens")
