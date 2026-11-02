# Pre-registration: re-reading the same jams to measure how fast entries leave

By MV2 of Munim, Inc. (mv2@munimtech.com). Written on 2 November 2026, made with AI agents
(Anthropic Claude) working in his name. Text CC BY 4.0, code Apache-2.0.

This file is committed on its own, **before** any re-read. The code that will do the reading and the
grading (`reread.py` 0.2.0, which reuses the unchanged reader in `jam_attrition.py` 0.1.0) and its tests
are committed right after it, also before any re-read. Thresholds and rules below will not be changed
after data is read; any later fix will be dated in the results and reported next to, never instead
of, the graded numbers.

## Why

The first count ([RESULTS.md](RESULTS.md)) read 1,352 finished jams once, on 1 November 2026, and found
that at least 3.4% of their ranked entries are gone from the results, more in older jams. One reading
can only compare jams of different ages. It cannot say how fast entries leave a given jam, and it has
two known weak spots: entries lost from the very bottom of a list leave no gap, and a host who ranked
by hand could have skipped rank numbers.

Reading the **same** jams again answers the rate question directly. The measure below compares the
number of entries listed then and now, so it sees bottom losses and does not use rank numbers at all.
Searches on 1 and 2 November 2026 found no repeated count of jam entries over time.

## Frame and reads

- **Jams:** exactly the 1,352 eligible jams in `data/jams.csv` (the base read, 2026-11-01 20:11:01 UTC),
  selected by `jam_attrition.eligible()`. No jam is added.
- **R1 (one month):** one re-read that begins between 28 and 45 days after the base read (29 November
  to 16 December 2026). Planned for the first days of December.
- **R2 (six months):** one re-read that begins between 170 and 200 days after the base read (20 April
  to 20 May 2027). Planned for early May 2027.
- Each re-read fetches results page 1 and the last results page of each jam (and the page before the
  last only when the last page is one tie group), one request per second, with a User-Agent that names
  MV2 and his email, as in the base read. About 2,700 requests, about 45 minutes.

## Measure (per jam)

- **L_base**, entries listed in the base read; **L_now**, entries listed at the re-read
  (20 × (pages − 1) + entries on the last page).
- **D = L_base − L_now**, entries that left the list. Negative if entries came back.
- A jam is **usable** when its re-read parses (status `ok`, or `tie_span`, whose listed count is still
  exact) and it shows no more ranked entries than at the base read. A results page that now answers
  404 or 410 is a **jam gone** (counted on its own, not in D). A jam with more ranked entries than
  before was re-ranked and is **renumbered** (not comparable). Anything else is **unreadable**.
- **Loss share** for a group of usable jams = ΣD / ΣL_base. 95% percentile intervals come from 2,000
  bootstrap resamples of jams (seed 20261202).
- **Age** = years from the end of the jam's submission period to the base read, in the same cohorts as
  before: under 1 year; 1–2; 2–3; 3–5; 5 years or more.

## Predictions

Core: Q1, Q2, Q3. Each read is graded on its own, with its own limits.

| | R1 (one month) | R2 (six months) |
|---|---|---|
| **Q1** (core) | loss share above 0, and its 95% interval above 0 | same |
| **Q2** (core) | loss share between 0.01% and 0.5% (inclusive) | between 0.1% and 3% (inclusive) |
| **Q3** (core) | jams under 1 year old lose a larger share than jams 5 years or older, and the 95% interval of the difference lies above 0 | same |
| **Q4** | at most 1% of the 1,352 jams are gone entirely | at most 3% |
| **Q5** | between 3% and 50% (inclusive) of usable jams lost at least one entry | between 10% and 80% |

Reasoning, stated so it can be checked: the base read fits about 0.9% a year overall, and the shape
by age (1.5% gone within the first year, then slower) says young jams lose entries several times faster
than old ones. One month at 0.9% a year is about 0.07%; the ranges are wide because losses come in
lumps (a host removing many entries at once).

## When a prediction is not graded

- If the re-read began outside its window (above), or more than 10% of the 1,352 jams are unreadable
  or renumbered, or fewer than 100 jams are usable, nothing in that read is graded.
- Q3 needs at least 30 usable jams under 1 year and 30 aged 5 or more.

`grade()` in `reread.py` applies exactly these rules; the results will quote its output.

## Reported but not predicted

Loss share by cohort, entries that came back, the counts of each status, and one yearly rate (loss
share × 365.25 / days elapsed), exploratory.

## Limits, stated in advance

- The frame is the most-joined past jams read on 1 November 2026, not a random sample of all jams.
- "Left the list" does not say why (deleted by the maker, removed by the host, a closed account).
- Two reads a month or six months apart cannot see entries that left and came back in between.

## Data and privacy

Only per-jam counts are published (jam slug, dates, L and N0 at each read, D). No game, author or
entry is named or stored.
