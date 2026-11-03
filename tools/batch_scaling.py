"""How compute-bound is decoding? From vLLM serve.log 10-second windows with little prompt reading (< PROMPT_MAX tok/s):
per-request generation rate r(S) vs running requests S. Step-time model T = a + b * n with n = S * (k+1) verified tokens
per step (k = 3 draft tokens): 1/r is linear in S, and a/b = (k+1) * intercept / slope. Then predicted throughput for
k = 0..4 draft tokens from the measured per-position acceptance rates (unconditional, as vLLM reports them).
usage: python -I batch_scaling.py <serve.log> [<serve.log> ...]"""
import collections
import re
import statistics as st
import sys

sys.stdout.reconfigure(encoding='utf-8')
RX = re.compile(r'Avg prompt throughput: ([\d.]+) tokens/s, Avg generation throughput: ([\d.]+) tokens/s, Running: (\d+) reqs')
RX_ACC = re.compile(r'Per-position acceptance rate: ([\d.]+), ([\d.]+), ([\d.]+)')
PROMPT_MAX = 1200.0
K = 3
by_s = collections.defaultdict(list)
acc = []
for path in sys.argv[1:]:
    for line in open(path, encoding='utf-8', errors='replace'):
        m = RX.search(line)
        if m:
            p, g, s = float(m.group(1)), float(m.group(2)), int(m.group(3))
            if p < PROMPT_MAX and s >= 4 and g > 50:
                by_s[s].append(g / s)
        m = RX_ACC.search(line)
        if m:
            acc.append(tuple(float(x) for x in m.groups()))
pts = [(s, st.median(v), len(v)) for s, v in sorted(by_s.items()) if len(v) >= 5]
print('running S: per-request tok/s (median, n windows)')
print('  ' + ' | '.join(f"S={s}: {r:.1f} (n={n})" for s, r, n in pts))
xs = [s for s, _, _ in pts]
ys = [1 / r for _, r, _ in pts]
ws = [n for _, _, n in pts]
mx = sum(w * x for w, x in zip(ws, xs)) / sum(ws)
my = sum(w * y for w, y in zip(ws, ys)) / sum(ws)
slope = sum(w * (x - mx) * (y - my) for w, x, y in zip(ws, xs, ys)) / sum(w * (x - mx) ** 2 for w, x in zip(ws, xs))
inter = my - slope * mx
ab = (K + 1) * inter / slope if slope > 0 else float('inf')
print(f"fit 1/r = {inter:.5f} + {slope:.6f} * S  ->  a/b = {ab:.1f} verified-token equivalents (fixed cost per step)")
p = [st.median(x[i] for x in acc) for i in range(3)] if acc else [0.75, 0.57, 0.45]
print(f"per-position acceptance (median of {len(acc)} windows): {p[0]:.3f}, {p[1]:.3f}, {p[2]:.3f}  -> mean length k=3: {1 + sum(p):.2f}")
# extrapolate a 4th position with the same ratio as 3rd/2nd
p4 = p[2] * p[2] / p[1]
cum = [0.0, p[0], p[0] + p[1], p[0] + p[1] + p[2], p[0] + p[1] + p[2] + p4]
S = 18
base = None
for k in range(0, 5):
    accepted = S * (1 + cum[k])
    t = ab + S * (k + 1)
    thr = accepted / t
    base = thr if k == K else base
    print(f"  k={k}: accepted/step {accepted:5.1f}, verified/step {S * (k + 1):3d}, relative throughput {thr:.4f}")
print('relative to k=3: ' + ', '.join(f"k={k}: {100 * ((S * (1 + cum[k])) / (ab + S * (k + 1)) / base - 1):+.1f}%" for k in range(0, 5)))
