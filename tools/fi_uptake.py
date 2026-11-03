"""First-impression uptake: for every turn whose user prompt holds a FIRST IMPRESSIONS block, does the player's thinking
in that turn (and the next one) refer to it? Prints counts and a short excerpt per case.
usage: python -I fi_uptake.py <results_dir> [max_examples]"""
import glob
import os
import re
import sys

sys.stdout.reconfigure(encoding='utf-8')
RES = sys.argv[1]
MAX_EX = int(sys.argv[2]) if len(sys.argv) > 2 else 12
RX_TURN = re.compile(r'^--- analysis_step=(\d+) \| action=(\d+) .*$', re.M)
RX_REF = re.compile(r'(?i)(first[- ]impression|fresh (model|instance)|impressions?\b|hypothes[ie]s [ABC]\b|\b[AB]\)\s*(says|suggests|hypothes)|'
                    r'option [AB]\b|suggestion [AB]\b|(A|B)\'s (hypothes|idea|suggest)|from (A|B)\b)')
n_turns = n_ref = n_ref_next = 0
examples = []
for path in sorted(glob.glob(os.path.join(RES, 'transcripts', '*_p0.txt'))):
    game = os.path.basename(path)[:4]
    text = open(path, encoding='utf-8', errors='replace').read()
    marks = list(RX_TURN.finditer(text))
    turns = [text[m.start():(marks[i + 1].start() if i + 1 < len(marks) else len(text))] for i, m in enumerate(marks)]
    for i, t in enumerate(turns):
        up = t.find('[USER PROMPT]')
        if up < 0 or 'FIRST IMPRESSIONS (fresh model' not in t[up:t.find('[MODEL RESPONSE META]', up) if '[MODEL RESPONSE META]' in t[up:] else len(t)]:
            continue
        thinking = ' '.join(re.findall(r'\[THINKING\]\n(.*?)(?=\n\[[A-Z ]+\]\n|\Z)', t, flags=re.S))
        if not thinking.strip():
            continue
        n_turns += 1
        m = RX_REF.search(thinking)
        nxt = turns[i + 1] if i + 1 < len(turns) else ''
        thinking_next = ' '.join(re.findall(r'\[THINKING\]\n(.*?)(?=\n\[[A-Z ]+\]\n|\Z)', nxt, flags=re.S))
        if m:
            n_ref += 1
            if len(examples) < MAX_EX:
                s = max(0, m.start() - 200)
                examples.append(f"{game} step {RX_TURN.match(t).group(1)}: ...{thinking[s:m.end() + 300]}...".replace('\n', ' '))
        elif RX_REF.search(thinking_next):
            n_ref_next += 1
print(f"turns with a first-impressions block and thinking: {n_turns}; thinking refers to it in the same turn: {n_ref} "
      f"({100 * n_ref / max(1, n_turns):.0f}%); only in the next turn: {n_ref_next}")
for e in examples:
    print('-', e[:700])
