# Results: vanished entries in itch.io jam results

By MV2 of Munim, Inc. (mv2@munimtech.com), made with AI agents (Anthropic Claude) working in his name.
Written on 2 November 2026. Text and data CC BY 4.0, code Apache-2.0.

This grades the predictions in [PREREGISTRATION.md](PREREGISTRATION.md) exactly as written there. The
data job (`jam_attrition.py` 0.1.0) first checked that the pre-registration and the same code were
public in this repository (seen 2026-11-01 20:11:00 UTC; SHA-256 of PREREGISTRATION.md `fc9310b3...2359`,
of jam_attrition.py `2131e9e7...54d6`), then read itch.io from 20:11 to 21:04 UTC on 1 November 2026
(2,956 requests, one per second). Nothing in the code or the thresholds was changed after the read.

## Answer in one paragraph

Of 211,101 entries ranked in 1,352 finished itch.io jams (the most-joined past jams), at least 7,166
(3.4%, 95% interval 3.2% to 3.7%) are no longer in their jam's results list today. The share grows with
age: 1.5% for jams under a year old, 2.4% at 1 to 2 years, 2.9% at 2 to 3, 4.1% at 3 to 5 and 4.8% for
jams 5 years old or more. 96% of the jams aged 5 or more have lost at least one entry. Low-ranked
entries vanish far more often than top-ranked ones: in jams 2 years or older with at least 3 results
pages, 9.8% of the rank slots on the last results page are empty, against 1.8% of those on page 1.
All six predictions held.

## Grades

| | Prediction (as pre-registered) | Measured | Grade |
|---|---|---|---|
| **P1** (core) | 5y+ pooled share > under-2y share, 95% interval of the difference above 0 | 4.81% vs 1.91%; difference +2.90 points (95% +2.30 to +3.52) | **held** |
| **P2** (core) | 5y+ pooled share between 3% and 15% | 4.81% (95% 4.27% to 5.37%; 325 jams) | **held** |
| **P3** (core) | under-1y pooled share below 3% | 1.51% (95% 1.25% to 1.85%; 246 jams) | **held** |
| P4 | Spearman rho(age, V/N0) > 0.10, one-sided permutation p < 0.05 (jams with N0 >= 30) | rho 0.435 (1,279 jams), p 0.0005 (none of 2,000 permutations reached it) | **held** |
| P5 | >= 80% of 5y+ jams lost at least one entry | 312 of 325 = 96.0% (Wilson 95% 93.3% to 97.7%) | **held** |
| P6 | bottom region > top region, interval above 0 (jams 2y+ with >= 3 results pages) | 9.77% vs 1.79%; difference +7.99 points (95% +7.21 to +8.81; 695 jams) | **held** |

Core 3 of 3, all 6 of 6. The reader check passed: 2 of 1,471 results pages read (0.14%) were unusable,
against a 10% limit.

## By age

| Age at reading | Jams | Entries ranked (N0) | Vanished (V) | Pooled share (95%) | Median jam | Jams with any loss | Live entry count now below rated count |
|---|---|---|---|---|---|---|---|
| under 1 year | 246 | 35,350 | 535 | 1.51% (1.25-1.85) | 1.57% | 174 (71%) | 118 |
| 1-2 years | 234 | 31,273 | 737 | 2.36% (2.07-2.71) | 2.00% | 178 (76%) | 126 |
| 2-3 years | 204 | 33,330 | 956 | 2.87% (2.33-3.53) | 2.99% | 174 (85%) | 107 |
| 3-5 years | 343 | 54,955 | 2,237 | 4.07% (3.64-4.64) | 3.95% | 304 (89%) | 272 |
| 5 years or more | 325 | 56,193 | 2,701 | 4.81% (4.27-5.37) | 4.60% | 312 (96%) | 301 |
| **all** | **1,352** | **211,101** | **7,166** | **3.39% (3.15-3.66)** | | | |

Exploratory (not predicted): one constant yearly rate fitted to all jams is 0.89% of a jam's ranked
entries a year. The curve is not a straight line from zero, though: jams under a year old have already
lost 1.5%, so much of the loss comes early (entries taken down soon after results), with a slower,
steady loss after that.

## How it was counted (short)

itch.io keeps a finished jam's original rank numbers. When an entry is deleted or taken out of the jam,
its rank number is left unused. For each jam the reader fetched results page 1 and the last results page:
N0 = last rank + entries tied at it - 1; L = 20 x (pages - 1) + entries on the last page; V = N0 - L.
Ties are not gaps. An entry that vanished from the very bottom of the list leaves no gap, so V is a
**lower bound**.

Frame: 1,965 jam links on pages 1-40 of itch.io's past-jams list (most joined first); 1,472 link a
results page and all were read. 1,387 parsed cleanly (`ok`); 77 had no ranks (unranked jams), 5 had a
tie group spanning the page break (excluded, as planned), 2 were inconsistent and 1 returned 404.
Eligible after the date and size rules (submission ended by 30 September 2026, N0 >= 10): 1,352.

## Checked by hand before publishing

The counts were checked against itch.io pages read by hand on 2 November 2026:

| Jam | Last page read by hand | N0 | L | V | Job's row |
|---|---|---|---|---|---|
| game-off-2019 | (design-time example) ends with six tied at #227, page 11 of 11 | 232 | 219 | 13 | 232, 219, 13 |
| game-off-2022 | page 27 of 27: 20 entries, last three tied at #551 | 553 | 540 | 13 | 553, 540, 13 |
| brackeys-6 | page 85 of 85: 8 entries, last one #1756 | 1,756 | 1,688 | 68 | 1,756, 1,688, 68 |
| gmtk-2019 | page 126 of 126: 8 entries, last two tied at #2609 | 2,610 | 2,508 | 102 | 2,610, 2,508, 102 |

GMTK Game Jam 2019 also shows the second, independent sign: its header now says 2,540 entries were
submitted, while 2,610 entries were rated at the time.

## Limits

- **Design-time reads shaped the thresholds.** Before the pre-registration, a handful of pages were
  read by hand (listed in PREREGISTRATION.md), including Game Off 2019 at 5.6%. P2's range and P3's
  limit were set with those in view, so they are less of a test than P1, P4 and P6, which only say
  which way the effect goes.
- The frame is itch.io's most-joined past jams, not a random sample. Small jams may lose entries at a
  different rate.
- Age is not randomised. Older jams in the frame differ in other ways (for example, jams from before
  2020 that are still among the most joined are mostly large, well-known ones).
- "Vanished" means gone from the results list. The pages do not say why: a maker deleting a game, a
  host removing an entry, or an account being closed all look the same.
- itch.io lets a host set ranks by hand instead of by score ("manual rankings"), and a host who does so
  could skip rank numbers. Such a gap would be counted as a loss. The pre-registered reader cannot tell
  these jams apart, so this is a possible upward error for those jams. It cannot explain the age
  pattern or the gap between bottom and top unless hosts of older jams skipped more numbers near the
  bottom. The second, independent sign (the live entry count now below the frozen rated count in 924 of
  the 1,352 jams) does not depend on rank numbers at all.
- V is a lower bound (losses at the very bottom leave no gap), and 5 jams whose last page was one tie
  group carried from earlier pages were left out by rule.

## What this is for

Jam results are often used as data: in studies of what wins, in portfolios and in jam archives. This
count says how much of that record is already gone and how fast it goes: about one entry in 65 within
the first year, one in 20 after five years, and mostly from the bottom of the rankings. Anyone who
studies old jam results should expect the missing entries to be the low-ranked ones, which biases any
look back at "all entries" toward the better-placed games.

## Files

- `data/summary.json`: the job's summary, as produced (counts, cohorts, intervals, grades).
- `data/jams.csv`: one row per jam read: jam slug, submission dates, header counts, pages, N0, L, V and
  the top and bottom region counts. Jam slugs are public event names; no game, author or entry is
  named.
- Re-run: `python jam_attrition.py --out out` (live), or re-grade a saved read with
  `python jam_attrition.py --from-csv data/jams.csv --read-at "2026-11-01 20:11:01" --out out`.

Prior art (searches on 1 and 2 November 2026): no published count of vanished jam entries was found.
Vu and Bezemer (2020) study what makes itch.io jam entries rank high. Ludum Dare players and archive
projects (for example the community LudumData archive) describe lost entries one game at a time. With
Ludum Dare due to end in October 2028, preserving jam games matters more each year.
