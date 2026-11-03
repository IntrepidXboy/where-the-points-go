# Where the Points Go

**An open-model agent for ARC-AGI-3, and what limits it**

Lavin · Koris Lab · November 2026

This repository holds our entry for the ARC Prize 2026 ARC-AGI-3 competition on Kaggle: the agent notebook, the measurement scripts and a technical report. The final version, v60, scored **33.39** on the public leaderboard.

## Contents

| Folder | What it holds |
|---|---|
| `paper/` | The report *Where the Points Go: A measurement study of an open-model agent on ARC-AGI-3* (HTML and PDF) |
| `notebook/` | `arc-agi-3-combined-v60.ipynb`, the exact notebook behind the 33.39 run |
| `tools/` | The scripts behind the report's measurements |

## The agent

- **Model:** Qwen3.8-Flash-Next, a mixture-of-experts model with about 6B active parameters, served by vLLM with NVFP4/FP8 weights, 448 of 512 experts kept by REAP pruning, and three multi-token-prediction draft tokens.
- **Harness:** the public Duck harness (Tufa Labs) with Daniel Franzen's Milestone-2 patch, affectify's D′ scheduler and our changes, which are listed in the notebook's first cell. v60 adds an effort ladder after truncated replies and lighter history trims.
- **Budget:** 110 unseen games in nine hours on one RTX PRO 6000, 18 games at a time.

## Five findings

1. **The score is token-bound.** Later levels weigh more, so about 10% more effective thinking per game is worth about 2.4 points on the hidden games.
2. **Reading prompts costs about 15% of generation speed.** On this hybrid model the serving cache never reaches the agent's previous reply, so every reply is read again on the next turn.
3. **Tests on the public games are not valid for changes to what the agent reads.** An adviser component that looked neutral in a leakage-controlled public test scored about 4 points lower on the hidden games in both of its submissions.
4. **Stuck levels are mostly a lottery of the first reading.** The same model cleared 26 of 41 such levels in other runs, while search could not rescue them even when given the goal.
5. **Two mechanical changes to the token economy,** an effort ladder after truncated replies and lighter history trims, raised levels cleared per token by 4 to 26% in a controlled run.

## Running the notebook

On Kaggle, create a notebook in the ARC Prize 2026 ARC-AGI-3 competition, import `notebook/arc-agi-3-combined-v60.ipynb`, attach the inputs below, select the **RTX PRO 6000** accelerator and turn the internet off.

- Competition data: `arc-prize-2026-arc-agi-3`
- Models: `lordhansolo/qwen3-8-flash-next-mixed-nvfp4-fp8` (PyTorch, `hf-mixed-mtp-nvfp4`, version 1), `dfranzen/intel-qwen3.8-flash-next-w4a16-autoround` (version 1), `dfranzen/albucino-qwen3-8-flash-next-drafter` (version 1)
- Datasets: `lordhansolo/vllm-main-e975732-arc3`, `dfranzen/taaf-kaggle-source-bundle-copy`, `dfranzen/pennyroyal-v253`

The switches in the config cell (cell 4) turn each change on or off. A normal Save & Run plays for 30 minutes as a check; the full nine-hour run happens when Kaggle reruns the notebook for scoring.

## The tools

Each script reads a run's output files (the vLLM `serve.log`, `benchmark.json`, the requests and events logs, or transcripts) and prints tables. Run them with `python -I <script> ...`; the first lines of each script give its exact inputs.

| Script | What it measures |
|---|---|
| `token_anatomy.py` | Where a run's tokens go: cleared vs never-cleared levels, the first actions of a level, truncated replies |
| `prefill_cost.py` | How much prompt reading slows generation (fit over the server's 10-second windows) |
| `prefill_sources.py` | Where the prompt reading comes from: normal turns, history trims, cache misses, images |
| `reply_reread.py` | Whether the previous reply is read again on the next request |
| `cache_edge.py` | Exactly where the serving cache stops on the next request |
| `cache_breaks.py` | Why the prompt cache breaks: trims, rewrites of earlier messages, appends |
| `batch_scaling.py` | Decoding speed against concurrent requests, and the predicted best number of draft tokens |
| `levels_at_tokens.py` | Levels cleared at equal token spend, per run |
| `levels_same_games.py` | The same comparison, on exactly the same games for every run |
| `bench_levels_at_tokens.py` | The same comparison from `benchmark.json` alone |
| `session_lengths.py` | Tokens between history trims, and prompt growth per turn |
| `fi_uptake.py` | How often the agent's thinking used the first-impression adviser |
| `truncated_look.py` | What truncated replies look like and what happens next |

## Credits

Daniel Franzen (da-fr) for the Milestone-2 solution and checkpoints. Tufa Labs (Harold Bessis, Jeroen Cottaar, Isaiah Pressman, Andries Smit, Michal Tesnar, Stefano Viel) for the Duck harness and TAAF. keithtyser for the Duck v18 notebook. lordhansolo for the vLLM runtime, the NVFP4/FP8 checkpoint and the TAAF Kaggle launcher. affectify for the D′ scheduler. John Pezzulli, Mamy Ratsimbazafy and Gabriel Olympie for Pennyroyal SGLang. Intel and Albucino for quantized checkpoints. The ARC Prize Foundation for the benchmark.

The report and the scripts were written with the help of an AI assistant (Claude).

## Licence

Our own code and the report are released under the Apache License 2.0. Third-party code and weights keep their original licences.
