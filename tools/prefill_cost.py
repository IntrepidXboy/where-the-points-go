"""Does prompt reading (prefill) slow down generation? From vLLM serve.log 10-second stats lines, windows with >= 17
requests running: least-squares fit gen_tok_s = a + b * prompt_tok_s, plus binned means.
usage: python -I prefill_cost.py <serve.log> [<serve.log> ...]"""
import re
import statistics as st
import sys

sys.stdout.reconfigure(encoding='utf-8')
RX = re.compile(r'Avg prompt throughput: ([\d.]+) tokens/s, Avg generation throughput: ([\d.]+) tokens/s, Running: (\d+) reqs, '
                r'Waiting: (\d+) reqs')
for path in sys.argv[1:]:
    pts = []
    for line in open(path, encoding='utf-8', errors='replace'):
        m = RX.search(line)
        if m and int(m.group(3)) >= 17:
            pts.append((float(m.group(1)), float(m.group(2))))
    pts = pts[6:]                       # skip the start-up burst
    xs, ys = [p for p, _ in pts], [g for _, g in pts]
    mx, my = st.mean(xs), st.mean(ys)
    b = sum((x - mx) * (y - my) for x, y in pts) / sum((x - mx) ** 2 for x in xs)
    a = my - b * mx
    r = (sum((x - mx) * (y - my) for x, y in pts) /
         (sum((x - mx) ** 2 for x in xs) * sum((y - my) ** 2 for y in ys)) ** 0.5)
    print(f"{path}: {len(pts)} windows | mean prompt {mx:.0f} tok/s, mean gen {my:.0f} tok/s | fit gen = {a:.0f} "
          f"{b:+.3f} x prompt (r = {r:.2f}) -> gen with no prompt reading ~{a:.0f} ({100 * (a - my) / my:+.0f}% vs now)")
    bins = [(0, 1000), (1000, 2000), (2000, 3000), (3000, 4000), (4000, 99999)]
    print('   binned: ' + ' | '.join(
        f"prompt {lo}-{hi if hi < 99999 else '+'}: gen {st.mean([g for p, g in pts if lo <= p < hi]):.0f} (n={sum(1 for p, _ in pts if lo <= p < hi)})"
        for lo, hi in bins if any(lo <= p < hi for p, _ in pts)))
