# jam-attrition

How many entries of finished itch.io game jams have since vanished from their jam's results? An open,
pre-registered count by MV2 of Munim, Inc. (mv2@munimtech.com), made with AI agents (Anthropic
Claude) working in his name.

**Result (2 November 2026):** of 211,101 entries ranked in 1,352 of itch.io's most-joined finished jams,
at least 7,166 (3.4%) are gone from their jam's results today. The share grows with age, from 1.5% for
jams under a year old to 4.8% for jams 5 years or older, and low-ranked entries vanish far more often
than top-ranked ones (9.8% vs 1.8% of rank slots). All 6 pre-registered predictions held. Full write-up:
[RESULTS.md](RESULTS.md). Predictions, written before any data was read:
[PREREGISTRATION.md](PREREGISTRATION.md).

## The idea in one example

itch.io keeps a finished jam's original rank numbers. When an entry's game is deleted or taken out of
the jam, it drops out of the results list and its rank number goes unused. Game Off 2019's results
still end at rank #227 with six entries tied there, so 232 entries were ranked, yet 219 are listed
today: 13 have vanished. Reading two pages per jam (the first and the last results page) is enough to
count this for any ranked jam.

## Run it

    python -m unittest -v
    python jam_attrition.py --out out            # about 2,000 jams, about 1 request per second
    python jam_attrition.py --from-csv data/jams.csv --read-at "2026-11-01 20:11:01" --out out   # re-grade

Outputs: `out/summary.json` (counts, cohort shares, intervals and the graded predictions),
`out/jams.csv` (one row per jam: slug, dates, N0, L, V) and `out/ranks.jsonl` (the rank numbers read).
The 1 November 2026 read is in `data/`. No game, author or entry is named or stored.

## Licence

Code: Apache-2.0 (see LICENSE). Text and data: CC BY 4.0.

Related open work by MV2: [game-jam-ai-rules](https://github.com/munimtechnologies/game-jam-ai-rules)
(what jams say about AI) and [jam-ai-ranks](https://github.com/munimtechnologies/jam-ai-ranks).
