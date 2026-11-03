"""Token-matched progress: for every game of a run, the player's cumulative generated tokens (requests log, the player
only - side requests are not in it) when each level was cleared (events log: first action whose level is higher).
Prints, per run, levels cleared within B player tokens summed over the games that played at least B tokens, plus
the same per level index. Optional side cost per level start (first impressions) can be added with RUN:cost.
usage: python -I levels_at_tokens.py <project_dir> run[:side_tokens_per_level_start] ..."""
import collections
import glob
import json
import os
import re
import sys

sys.stdout.reconfigure(encoding='utf-8')
ROOT = sys.argv[1]
RX_TOK = re.compile(r'"completion_tokens": (\d+)')
RX_ACT = re.compile(r'"action": (\d+), "request_index_within_turn"')
BUDGETS = (20000, 40000, 60000, 80000)


def game_curve(run, game_prefix):
    ev = glob.glob(os.path.join(ROOT, f'results_{run}', 'artifacts', f'{game_prefix}*_p0_events.jsonl'))
    rq = glob.glob(os.path.join(ROOT, f'results_{run}', f'{game_prefix}*_p0_requests.jsonl'))
    if not ev or not rq:
        return None
    clear_at = {}             # level -> action_num at which the next level was first seen
    last_level = 1
    for line in open(ev[0], encoding='utf-8'):
        e = json.loads(line)
        if e.get('type') != 'action':
            continue
        lv = e.get('level')
        if isinstance(lv, int) and lv > last_level:
            for k in range(last_level, lv):
                clear_at.setdefault(k, e['action_num'])
            last_level = lv
        if e.get('state') == 'WIN' or e.get('run_complete') and e.get('level_completed'):
            clear_at.setdefault(last_level, e['action_num'])
    toks = []                 # (action index of the turn, completion tokens) in order
    for line in open(rq[0], encoding='utf-8'):
        tail = line[-600:]
        if '"event": "response"' not in line[-3000:]:
            continue
        m, a = RX_TOK.search(line[-3000:]), RX_ACT.search(tail)
        toks.append((int(a.group(1)) if a else None, int(m.group(1)) if m else 0))
    total = sum(t for _, t in toks)
    cum_at = {}
    for level, act in clear_at.items():
        cum_at[level] = sum(t for a, t in toks if a is not None and a <= act)
    return total, cum_at, last_level


specs = []
for arg in sys.argv[2:]:
    run, _, cost = arg.partition(':')
    specs.append((run, float(cost or 0)))
games = sorted({os.path.basename(p)[:4] for p in glob.glob(os.path.join(ROOT, 'results_v47', '*_p0_requests.jsonl'))})
print(f"{'run':10} " + ' '.join(f"{'<=' + str(b // 1000) + 'K':>14}" for b in BUDGETS) + '   (levels / games that played >= B)')
for run, cost in specs:
    row = []
    per_level = collections.Counter()
    for b in BUDGETS:
        lv = n = 0
        for g in games:
            c = game_curve(run, g)
            if c is None:
                continue
            total, cum_at, _ = c
            n_starts = len(cum_at) + 1
            if total + cost * n_starts < b:
                continue
            n += 1
            for level, t in sorted(cum_at.items()):
                if t + cost * level <= b:      # level starts so far = level (incl. the first)
                    lv += 1
                    if b == BUDGETS[-1]:
                        per_level[level] += 1
        row.append(f"{lv:3d}/{n:2d} = {lv / max(1, n):4.2f}")
    print(f"{run + (' +' + str(int(cost)) if cost else ''):10} " + ' '.join(f"{x:>14}" for x in row))
