"""Token-matched progress from benchmark.json ONLY (no request logs needed): per game, the cumulative generated tokens
(history[*].generated_tokens - everything charged to the game, side requests included) at the action that cleared each
level (actions_per_level). For each budget B: levels cleared within B tokens, on the games where the REFERENCE run
used >= B tokens, for every run on exactly those games. usage: python -I bench_levels_at_tokens.py <project_dir> <ref> run ..."""
import json
import os
import sys

sys.stdout.reconfigure(encoding='utf-8')
ROOT, RUNS = sys.argv[1], sys.argv[2:]
BUDGETS = (20000, 40000, 60000, 80000, 120000, 160000, 200000)


def curves(run):
    """game -> (tokens used, [tokens at each level clear], finished all levels)"""
    b = json.load(open(os.path.join(ROOT, f'results_{run}', 'benchmark.json'), encoding='utf-8'))
    out = {}
    for g in b['game_runs']:
        hist = g.get('history') or []
        cum, tot = [], 0
        for h in hist:
            tot += int(h.get('generated_tokens') or 0)
            cum.append(tot)
        clears, k = [], 0
        for n_lv, acts in enumerate(g.get('actions_per_level') or []):
            if n_lv >= int(g.get('levels_completed') or 0):
                break
            k += int(acts)
            if k <= 0 or k > len(cum):
                break
            clears.append(cum[k - 1])
        finished = int(g.get('levels_completed') or 0) >= int(g.get('number_of_levels') or 99)
        out[g['game_id'][:4]] = (tot, clears, finished)
    return out


C = {r: curves(r) for r in RUNS}
ref = RUNS[0]
print(f"reference {ref}: per budget, the games it used >= B tokens on; every run scored on those games (levels per game)")
print('budget ' + ' '.join(f"{r:>10}" for r in RUNS))
for B in BUDGETS:
    # a game counts at budget B when the run used >= B tokens on it, or finished it (all its levels count);
    # a game the run stopped on (time ran out) before B is censored and left out
    sel = [g for g, (tot, _, fin) in C[ref].items() if tot >= B or fin]
    if not sel:
        continue
    row = []
    for r in RUNS:
        ok = [g for g in sel if g in C[r] and (C[r][g][0] >= B or C[r][g][2])]
        lv = sum(sum(1 for t in C[r][g][1] if t <= B) for g in ok)
        row.append(f"{lv / max(1, len(ok)):5.2f}/{len(ok):2d}")
    print(f"{B // 1000:4d}K  " + ' '.join(f"{x:>10}" for x in row) + f"   ({len(sel)} games)")
