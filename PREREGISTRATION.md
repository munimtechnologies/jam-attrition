# Pre-registration: vanished entries in itch.io jam results

By MV2 of Munim, Inc. (mv2@munimtech.com). Written on 1 November 2026, made with AI agents
(Anthropic Claude) working in his name. Text CC BY 4.0, code Apache-2.0.

This file, `jam_attrition.py` (the reader, the counting and the grading) and its tests are committed
**before** the data job reads any page in the frame. The job's first step (`wait_prereg.py`) waits until
this file and the same `jam_attrition.py` are public on GitHub, records their SHA-256 hashes, and only
then starts reading. Thresholds and rules below will not be changed after data is read; any later fix to
the reader will be dated in the results and reported next to, never instead of, the graded numbers.

## Question

How many entries of finished itch.io game jams have since vanished from their jam's results, and does
that share grow with the jam's age?

A search on 1 November 2026 found no published count. The closest work, Vu and Bezemer's 2020 study of
itch.io jams (ACM, doi 10.1145/3402942.3402981), looks at what makes entries rank high, not at whether
they are still there; Ludum Dare archive threads report dead links one game at a time.

## Why it can be measured

itch.io keeps a finished jam's original rank numbers on its results pages. When an entry's game is
deleted, or the entry is taken out of the jam, it drops out of the list and its rank number is left
unused. Example, read by hand while designing this study: Game Off 2019's last results page (page 11
of 11) ends with six entries tied at rank #227, so 232 entries were ranked, but only 219 are listed
today (13 gone). Ties are not gaps: five entries tied at #216 are followed by #221.

Pages read by hand while designing, before this file: results page 1 of GMTK Game Jam 2019, Game Off
2019 and Brackeys Game Jam 2020.1, Game Off 2019's page 11, page 50 of the past-jams list, and Game
Off 2025's results page 1 saved by an earlier study. Their numbers shaped the thresholds below; that is
stated here so readers can weigh it.

## Frame

Every jam linked from pages 1 to 40 of `https://itch.io/jams/past?page=N` (itch.io's default order for
past jams, most joined first; about 2,000 jams), read once on the day the job runs. A slug linked from
20 or more of the 40 pages is site navigation and is dropped. Only jams whose listing links a results
page are read (if no page links any results, every jam is read).

For each jam the reader fetches results page 1 and the last results page (and, only when the whole
last page is one tie group, the page before it): at most 3 requests per jam, one request per second,
with a User-Agent that names MV2 and his email. Only pages that itch.io's robots.txt allows are read.

## Measures (per jam)

- **N0**, entries ranked at results time = rank of the last listed entry + entries tied at it − 1.
- **L**, entries listed today = 20 × (pages − 1) + entries on the last page.
- **V = N0 − L**, vanished entries. Entries that vanished from the very bottom of the list leave no
  gap, and a tie group that spans a page break is counted only from the pages read, so V is a lower
  bound.
- **Age** = years from the end of the submission period (from the results header) to the read time.
- Top region: the rank slots covered by results page 1; bottom region: the slots on the last page after
  any tie group carried over from the page before.

**Eligible jams:** status `ok` (parsed, page 1 holds 20 entries when there is more than one page, ranks
in order, N0 ≥ L), submission period ended on or before 30 September 2026, and N0 ≥ 10.

**Pooled share** for a group of jams = ΣV / ΣN0. Intervals are 95% percentile intervals from 2,000
bootstrap resamples of jams (seed 20261101).

Age cohorts: under 1 year; 1–2; 2–3; 3–5; 5 years or more.

## Predictions

Core: P1, P2, P3.

- **P1.** The pooled share of jams aged 5 years or more is higher than that of jams aged under 2 years,
  and the 95% interval of the difference lies above 0.
- **P2.** The pooled share of jams aged 5 years or more is between 3% and 15% (inclusive).
- **P3.** The pooled share of jams aged under 1 year is below 3%.
- **P4.** Across eligible jams with N0 ≥ 30, Spearman's rho between age and the jam's own share V/N0 is
  above 0.10, with a one-sided permutation p below 0.05 (2,000 permutations).
- **P5.** At least 80% of eligible jams aged 5 years or more have at least one vanished entry.
- **P6.** Among eligible jams aged 2 years or more with at least 3 results pages, the pooled share of
  the bottom region is higher than that of the top region (low-ranked entries vanish more often), and
  the 95% interval of the difference lies above 0.

## When a prediction is not graded

- **Reader check:** if more than 10% of the results pages read come back unusable (status
  `inconsistent`, `page_size`, `last_page_empty`, or no submission dates), no prediction is graded.
- P1 needs at least 30 eligible jams aged 5+ and at least 30 aged under 2; P2 and P5 need 30 aged 5+;
  P3 needs 30 aged under 1; P4 and P6 need 30 jams in their sets. Otherwise the prediction is
  reported as "not graded".

`grade()` in `jam_attrition.py` applies exactly these rules; the results will quote its output.

## Reported but not predicted

Shares for every cohort and their intervals, the median jam's share, how many jams' live "entries
were submitted" count is now below their "given to N entries" rated count (a second, independent
sign of loss), and one constant yearly rate fitted to all jams (exploratory).

## Limits, stated in advance

- The frame is the most-joined past jams, not a random sample of all jams.
- "Vanished" means gone from the results list: deleted by its maker, taken out by the host, or lost
  with a closed account. The pages do not say which.
- V is a lower bound (see above), and age is not randomised: older jams also differ in other ways.

## Data and privacy

The job publishes per-jam counts (jam slug, dates, N0, L, V) and the rank numbers it read. No game,
author or entry is named or stored.
