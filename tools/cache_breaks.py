"""Why does the prompt cache break? For one game's requests log: for each request, compare its messages with the
previous request's messages + reply; find the first changed message; classify the break (trim = messages removed,
rewrite = an earlier message changed in place, append = nothing earlier changed) and what changed in the rewritten
message (images removed, text shortened, ...). Re-read size taken from usage (prompt - cached).
usage: python -I cache_breaks.py <requests.jsonl> [max_examples]"""
import collections
import json
import sys

sys.stdout.reconfigure(encoding='utf-8')
path = sys.argv[1]
MAX_EX = int(sys.argv[2]) if len(sys.argv) > 2 else 6


def parts(msg):
    c = msg.get('content')
    if isinstance(c, str):
        return [('text', c)]
    out = []
    for p in c or []:
        if isinstance(p, dict):
            if p.get('type') == 'text':
                out.append(('text', p.get('text', '')))
            else:
                out.append(('image', str(p)[:120]))
    return out


def summarize_change(a, b):
    pa, pb = parts(a), parts(b)
    ia, ib = sum(1 for t, _ in pa if t == 'image'), sum(1 for t, _ in pb if t == 'image')
    ta, tb = sum(len(x) for t, x in pa if t == 'text'), sum(len(x) for t, x in pb if t == 'text')
    keys = sorted(set(a) | set(b))
    other = [k for k in keys if k != 'content' and a.get(k) != b.get(k)]
    return f"role {a.get('role')}: images {ia}->{ib}, text chars {ta}->{tb}" + (f", fields changed {other}" if other else "")


prev_msgs = None
pending_reply = None
stats = collections.Counter()
reread = collections.Counter()
examples = collections.defaultdict(list)
for line in open(path, encoding='utf-8'):
    r = json.loads(line)
    ev = r.get('event')
    msgs = r.get('messages') or []
    if ev == 'request':
        cur = [json.dumps(m, sort_keys=True) for m in msgs]
        if prev_msgs is not None:
            n = min(len(prev_msgs), len(cur))
            j = next((i for i in range(n) if prev_msgs[i] != cur[i]), n)
            if j >= len(prev_msgs):
                kind = 'append'
            elif len(cur) < len(prev_msgs):
                kind = 'trim'
            else:
                kind = 'rewrite'
            stats[kind] += 1
            r_pos = j / max(1, len(cur))
            last = (kind, j, len(prev_msgs), len(cur), r_pos)
            if kind != 'append' and len(examples[kind]) < MAX_EX:
                a, b = json.loads(prev_msgs[j]), json.loads(cur[j])
                examples[kind].append(f"break at message {j} of {len(cur)} (prev {len(prev_msgs)}): " + summarize_change(a, b))
            pending_reply = last
        prev_msgs = cur
    elif ev == 'response' and pending_reply is not None:
        u = r.get('usage') or {}
        unc = int(u.get('prompt_tokens') or 0) - int((u.get('prompt_tokens_details') or {}).get('cached_tokens') or 0)
        kind = pending_reply[0]
        bucket = 'big' if unc >= 20000 else ('mid' if unc >= 5000 else 'small')
        reread[(kind, bucket)] += 1
        reread[(kind, 'tokens')] += max(0, unc)
print('request transitions:', dict(stats))
for kind in ('append', 'rewrite', 'trim'):
    print(f"  {kind:8}: re-read buckets small/mid/big = {reread[(kind, 'small')]}/{reread[(kind, 'mid')]}/{reread[(kind, 'big')]}, "
          f"uncached tokens {reread[(kind, 'tokens')] / 1e3:.0f}K")
for kind, ex in examples.items():
    print(f"--- {kind} examples:")
    for e in ex:
        print('   ', e[:300])
