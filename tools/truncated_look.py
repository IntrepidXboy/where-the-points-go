"""Truncated replies (finish_reason: length) in a run's transcripts: how repetitive is their thinking (share of
duplicate 200-char chunks; compression ratio), what happened on the next request, and a short excerpt of the end.
usage: python -I truncated_look.py <results_dir> [examples]"""
import glob
import os
import re
import sys
import zlib

sys.stdout.reconfigure(encoding='utf-8')
RES = sys.argv[1]
N_EX = int(sys.argv[2]) if len(sys.argv) > 2 else 4
rows = []
for path in sorted(glob.glob(os.path.join(RES, 'transcripts', '*_p0.txt'))):
    game = os.path.basename(path)[:4]
    text = open(path, encoding='utf-8', errors='replace').read()
    # blocks: [MODEL RESPONSE META] ... [THINKING] ... until next [SECTION]
    for m in re.finditer(r'\[MODEL RESPONSE META\]\nfinish_reason: (\w+)(.*?)\n\[THINKING\]\n(.*?)(?=\n\[[A-Z ]+\]\n|\Z)', text, flags=re.S):
        fin, meta, think = m.group(1), m.group(2), m.group(3)
        if fin != 'length':
            continue
        chunks = [think[i:i + 200] for i in range(0, max(0, len(think) - 200), 200)]
        dup = 1 - len(set(chunks)) / max(1, len(chunks))
        comp = len(zlib.compress(think.encode('utf-8'))) / max(1, len(think.encode('utf-8')))
        after = text[m.end():m.end() + 3000]
        nxt = re.search(r'\[MODEL RESPONSE META\]\nfinish_reason: (\w+)', after)
        rows.append((game, len(think), dup, comp, nxt.group(1) if nxt else '?', think[-600:]))
print(f"truncated replies: {len(rows)}")
if rows:
    loops = sum(1 for r in rows if r[2] > 0.3 or r[3] < 0.12)
    print(f"  look like loops (>30% duplicate chunks or compress < 0.12): {loops}; median chars {sorted(r[1] for r in rows)[len(rows) // 2]}")
    print(f"  duplicate-chunk share per reply: " + ', '.join(f"{r[2]:.2f}" for r in rows[:40]))
    print(f"  next reply's finish: " + ', '.join(r[4] for r in rows[:40]))
    for game, n, dup, comp, nxt, tail in rows[:N_EX]:
        print(f"--- {game}: {n} chars, dup {dup:.2f}, compress {comp:.2f}, next {nxt}\n...{tail.replace(chr(10), ' ')[-500:]}")
