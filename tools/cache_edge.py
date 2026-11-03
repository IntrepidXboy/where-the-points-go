"""Where exactly does the cache stop on the next request? For consecutive (request i, request i+1) of a game:
diff = cached_tokens(i+1) - prompt_tokens(i). Cache ends at the previous prompt's end (rounded to a block) ->
diff in [-block, 0]; cache reaches into the reply -> diff > 0 (then it broke inside the reply, e.g. a text mismatch).
usage: python -I cache_edge.py <project_dir> run"""
import collections
import glob
import json
import os
import sys

sys.stdout.reconfigure(encoding='utf-8')
ROOT, run = sys.argv[1], sys.argv[2]
hist = collections.Counter()
diffs = []
for rq in sorted(glob.glob(os.path.join(ROOT, f'results_{run}', '*_p0_requests.jsonl'))):
    prev_prompt = prev_completion = None
    for line in open(rq, encoding='utf-8'):
        if '"event": "response"' not in line[-3000:]:
            continue
        u = (json.loads(line).get('usage') or {})
        p = int(u.get('prompt_tokens') or 0)
        c = int((u.get('prompt_tokens_details') or {}).get('cached_tokens') or 0)
        if prev_prompt is not None and p > prev_prompt:          # no trim
            d = c - prev_prompt
            diffs.append((d, prev_completion))
            if d < -2048:
                hist['cache ends >2K before the previous prompt end'] += 1
            elif d < -128:
                hist['ends 128-2048 before'] += 1
            elif d <= 0:
                hist['ends within 128 tokens before the previous prompt end'] += 1
            elif d <= 64:
                hist['reaches 1-64 tokens into the reply'] += 1
            else:
                hist['reaches >64 tokens into the reply'] += 1
        prev_prompt, prev_completion = p, int(u.get('completion_tokens') or 0)
n = sum(hist.values())
for k, v in hist.most_common():
    print(f"{100 * v / n:5.1f}%  {k}")
pos = sorted(d for d, _ in diffs if d > 0)
if pos:
    print('when the cache reaches into the reply: median', pos[len(pos) // 2], 'tokens; share of that reply cached ~',
          round(sum(min(d, comp) for d, comp in diffs if d > 0) / max(1, sum(comp for d, comp in diffs if d > 0)), 3))
neg = sorted(d for d, _ in diffs if d <= 0)
print('when it stops before: median', neg[len(neg) // 2] if neg else None, 'tokens (block alignment)')
