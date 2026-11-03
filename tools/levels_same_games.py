"""Same-game token-matched comparison: for each budget B, the games where the REFERENCE run played >= B player tokens;
every run is scored on exactly those games (levels cleared within B player tokens + side cost per level start).
usage: python -I levels_same_games.py <project_dir> <ref_run[:cost]> run[:cost] ..."""
import os, sys, importlib.util
sys.stdout.reconfigure(encoding='utf-8')
spec = importlib.util.spec_from_file_location('lat', os.path.join(os.path.dirname(os.path.abspath(__file__)), 'levels_at_tokens.py'))
ROOT = sys.argv[1]
src = open(spec.origin, encoding='utf-8').read().split("specs = []")[0]
ns = {'__name__': 'lat'}
sys.argv = [sys.argv[0], ROOT] + sys.argv[2:]
exec(compile(src, 'lat', 'exec'), ns)
game_curve, BUDGETS = ns['game_curve'], (20000, 40000, 60000, 80000)
import glob
games = sorted({os.path.basename(p)[:4] for p in glob.glob(os.path.join(ROOT, 'results_v47', '*_p0_requests.jsonl'))})
specs = [(a.partition(':')[0], float(a.partition(':')[2] or 0)) for a in sys.argv[2:]]
ref, ref_cost = specs[0]
curves = {(r, g): game_curve(r, g) for r, _ in specs for g in games}
def levels_within(c, b, cost):
    total, cum_at, _ = c
    return sum(1 for level, t in cum_at.items() if t + cost * level <= b)
print(f"reference {ref}: per budget, the games it played >= B tokens; every run on those games (levels / games)")
for b in BUDGETS:
    sel = [g for g in games if curves[(ref, g)] and curves[(ref, g)][0] + ref_cost * (len(curves[(ref, g)][1]) + 1) >= b]
    parts = []
    for r, cost in specs:
        ok = [g for g in sel if curves[(r, g)] and curves[(r, g)][0] + cost * (len(curves[(r, g)][1]) + 1) >= b]
        lv = sum(levels_within(curves[(r, g)], b, cost) for g in ok)
        parts.append(f"{r}{'+' + str(int(cost)) if cost else ''} {lv}/{len(ok)}={lv / max(1, len(ok)):.2f}")
    print(f"<= {b // 1000}K on {len(sel)} games: " + " | ".join(parts))
