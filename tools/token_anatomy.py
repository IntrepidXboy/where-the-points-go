"""Where do a run's tokens go? From the requests logs (player replies: completion tokens, finish reason, action index)
and the events logs (level of every action), per run:
- share of tokens on levels that were cleared vs levels never cleared (sinks);
- on cleared levels: tokens before the level's first action, in its first 5 actions, and the rest;
- truncated replies (finish 'length'): count and tokens;
- replies > 8K tokens: count, tokens, how many still ended with a tool call.
usage: python -I token_anatomy.py <project_dir> run [run ...]"""
import collections
import glob
import json
import os
import re
import statistics as st
import sys

sys.stdout.reconfigure(encoding='utf-8')
ROOT = sys.argv[1]
RX_TOK = re.compile(r'"completion_tokens": (\d+)')
RX_ACT = re.compile(r'"action": (\d+), "request_index_within_turn"')
RX_FIN = re.compile(r'"finish_reason": "([a-z_]+)"')

for run in sys.argv[2:]:
    tot = cleared_tok = sink_tok = pre_first = first5 = rest = 0
    trunc_n = trunc_tok = big_n = big_tok = big_tool = 0
    per_level_first5_share = []
    for rq in sorted(glob.glob(os.path.join(ROOT, f'results_{run}', '*_p0_requests.jsonl'))):
        g = os.path.basename(rq)[:4]
        ev = glob.glob(os.path.join(ROOT, f'results_{run}', 'artifacts', f'{g}*_p0_events.jsonl'))
        if not ev:
            continue
        level_of_action, max_level = {}, 1
        for line in open(ev[0], encoding='utf-8'):
            e = json.loads(line)
            if e.get('type') == 'action' and isinstance(e.get('level'), int):
                # the level the action was taken ON = level shown before it; approximate with the previous action's level
                level_of_action[e['action_num']] = e['level']
                max_level = max(max_level, e['level'])
        # level on which action k was taken: the level after action k-1 (action 0 = initial level 1)
        on_level = {}
        prev = 1
        for k in sorted(level_of_action):
            on_level[k] = prev
            prev = level_of_action[k]
        cleared_levels = {lv for lv in range(1, max_level)}
        rows = []
        for line in open(rq, encoding='utf-8'):
            tail = line[-3000:]
            if '"event": "response"' not in tail:
                continue
            m, a, f = RX_TOK.search(tail), RX_ACT.search(tail[-600:]), RX_FIN.search(tail[tail.index('"event": "response"'):])
            t = int(m.group(1)) if m else 0
            act = int(a.group(1)) if a else None
            fin = f.group(1) if f else ''
            rows.append((act, t, fin))
            tot += t
            if fin == 'length':
                trunc_n += 1
                trunc_tok += t
            if t > 8192:
                big_n += 1
                big_tok += t
                big_tool += fin == 'tool_calls'
        # the reply with action index k decides action k (the turn's action); tokens of the turn -> level on_level[k]
        by_level = collections.defaultdict(list)
        for act, t, fin in rows:
            if act is None:
                continue
            lv = on_level.get(act, prev)
            by_level[lv].append((act, t))
        for lv, items in by_level.items():
            s = sum(t for _, t in items)
            if lv in cleared_levels:
                cleared_tok += s
                acts = sorted({a for a, _ in items})
                first_act = acts[0] if acts else None
                first5_set = set(acts[:5])
                p = sum(t for a, t in items if a == first_act)
                f5 = sum(t for a, t in items if a in first5_set)
                pre_first += p
                first5 += f5
                rest += s - f5
                if s > 0:
                    per_level_first5_share.append(f5 / s)
            else:
                sink_tok += s
    print(f"{run}: tokens {tot / 1e6:.2f}M | on cleared levels {100 * cleared_tok / tot:.0f}% | on levels never cleared "
          f"{100 * sink_tok / tot:.0f}%")
    print(f"   cleared levels: first turn {100 * pre_first / max(1, cleared_tok):.0f}% of their tokens, first 5 action turns "
          f"{100 * first5 / max(1, cleared_tok):.0f}% (median per level {100 * st.median(per_level_first5_share):.0f}%)")
    print(f"   truncated replies: {trunc_n} = {trunc_tok / 1e3:.0f}K tokens ({100 * trunc_tok / tot:.1f}%) | replies >8K: {big_n} "
          f"= {big_tok / 1e3:.0f}K ({100 * big_tok / tot:.1f}%), {big_tool} of them still ended in a tool call")
