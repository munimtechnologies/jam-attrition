# jam-attrition

How many entries of finished itch.io game jams have since vanished from their jam's results? An open,
pre-registered count by MV2 of Munim, Inc. (mv2@munimtech.com), made with AI agents (Anthropic
Claude) working in his name.

**Status (1 November 2026):** pre-registered, no result yet. The predictions, the reader and the grading
code are in [PREREGISTRATION.md](PREREGISTRATION.md) and `jam_attrition.py`; the data job waits until
both are public here before it reads a single jam page.

## The idea in one example

itch.io keeps a finished jam's original rank numbers. When an entry's game is deleted or taken out of
the jam, it drops out of the results list and its rank number goes unused. Game Off 2019's results
still end at rank #227 with six entries tied there, so 232 entries were ranked, yet 219 are listed
today: 13 have vanished. Reading two pages per jam (the first and the last results page) is enough to
count this for any ranked jam.

## Run it

    python -m unittest -v
    python jam_attrition.py --out out            # about 2,000 jams, about 1 request per second

Outputs: `out/summary.json` (counts, cohort shares, intervals and the graded predictions),
`out/jams.csv` (one row per jam: slug, dates, N0, L, V) and `out/ranks.jsonl` (the rank numbers read).
No game, author or entry is named or stored.

## Licence

Code: Apache-2.0 (see LICENSE). Text and data: CC BY 4.0.

Related open work by MV2: [game-jam-ai-rules](https://github.com/munimtechnologies/game-jam-ai-rules)
(what jams say about AI) and [jam-ai-ranks](https://github.com/munimtechnologies/jam-ai-ranks).
