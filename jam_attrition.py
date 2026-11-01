#!/usr/bin/env python3
# jam-attrition: how many itch.io game-jam entries have vanished from their jam's results since.
# By MV2 of Munim, Inc., made with AI agents (Anthropic Claude). Apache-2.0.
"""itch.io keeps a finished jam's original rank numbers on its results pages, but an entry whose
game was deleted (or that was taken out of the jam) drops out of the list and leaves its rank
number unused. Game Off 2019, for example, still ends at rank #227 with six entries tied there,
so 232 entries were ranked, yet only 219 are listed today.

This script reads, for every ranked jam in a fixed frame (the first 40 pages of itch.io's past
jams list, which is sorted by most joined), two public pages per jam: results page 1 and the last
results page. From them it counts

  N0  ranked entries at results time   = last rank + (entries tied at that rank on the page) - 1
  L   entries still listed today      = 20 x (pages - 1) + entries on the last page
  V   vanished entries                = N0 - L

and grades the predictions in PREREGISTRATION.md against the jam's age. Entries that vanished
from the very bottom of a list leave no gap, so V is a lower bound.

    python jam_attrition.py --out out [--pages 40] [--delay 1.0] [--deadline-minutes 200]
    python jam_attrition.py --out out --offline out/raw     (re-parse saved pages, no network)

Only public pages that itch.io's robots.txt allows are read (/jams/past and /jam/<slug>/results),
one request per --delay seconds, with a User-Agent that names MV2 and his email. No game, author or
entry is recorded: only each jam's slug, dates and counts.
"""

import argparse
import csv
import datetime as dt
import json
import math
import os
import random
import re
import sys
import time
import urllib.error
import urllib.request

VERSION = "0.1.0"
UA = "MV2-Munim-jam-attrition/0.1 (MV2 of Munim, Inc.; mv2@munimtech.com)"
BASE = "https://itch.io"
PER_PAGE = 20
FRAME_PAGES = 40
LAST_END = "2026-09-30 23:59:59"   # jams whose submissions closed after this are left out
MIN_N0 = 10                        # jams with fewer ranked entries are left out
CHROME_PAGES = 20                  # a slug linked from this many listing pages is site chrome

LISTING_LINK = re.compile(r'href="(?:https://itch\.io)?/jam/([A-Za-z0-9_-]+)(/results)?"')
ORDINAL = re.compile(r'class="ordinal_rank">\s*(\d+)(?:st|nd|rd|th)\s*<', re.I)
ENTRIES_IN = re.compile(r'<strong>([\d,]+) entr(?:y|ies)</strong>\s*(?:were|was) submitted', re.I)
RATED = re.compile(r'<strong>([\d,]+) ratings?</strong>\s*(?:were|was) given to\s*<strong>([\d,]+) '
                   r'entr(?:y|ies)</strong>\s*\(([\d.]+)%\)', re.I)
WINDOW = re.compile(r'(?:were|was) submitted between\s*<span[^>]*>\s*(\d{4}-\d\d-\d\d \d\d:\d\d:\d\d)\s*</span>'
                    r'\s*and\s*<span[^>]*>\s*(\d{4}-\d\d-\d\d \d\d:\d\d:\d\d)\s*</span>', re.I)
PAGER = re.compile(r'[?&](?:amp;)?page=(\d+)')


# ---------------------------------------------------------------- parsing

def parse_listing(page):
    """[(slug, has_results_link)] in the order the slugs first appear on one past-jams page."""
    seen = {}
    for slug, results in LISTING_LINK.findall(page):
        if slug not in seen:
            seen[slug] = False
        if results:
            seen[slug] = True
    return list(seen.items())


def frame_from_listings(pages):
    """Slugs in the frame, in listing order, from the raw listing pages: a slug linked from
    CHROME_PAGES or more listing pages is site chrome and is dropped; a slug counts as ranked if
    any listing page links its results."""
    counts, order, ranked = {}, [], {}
    for page in pages:
        for slug, has_results in parse_listing(page):
            counts[slug] = counts.get(slug, 0) + 1
            if slug not in ranked:
                order.append(slug)
                ranked[slug] = False
            ranked[slug] = ranked[slug] or has_results
    return [(s, ranked[s]) for s in order if counts[s] < CHROME_PAGES]


def num(s):
    return int(s.replace(",", ""))


def parse_header(page):
    """Counts and dates from the summary at the top of a results page (None where absent)."""
    out = {"submitted": None, "ratings": None, "rated": None, "rated_pct": None, "sub_start": None,
           "sub_end": None}
    m = ENTRIES_IN.search(page)
    if m:
        out["submitted"] = num(m.group(1))
    m = RATED.search(page)
    if m:
        out["ratings"], out["rated"], out["rated_pct"] = num(m.group(1)), num(m.group(2)), float(m.group(3))
    m = WINDOW.search(page)
    if m:
        out["sub_start"], out["sub_end"] = m.group(1), m.group(2)
    return out


def parse_ranks(page):
    """The rank shown for each listed entry, in page order."""
    return [int(r) for r in ORDINAL.findall(page)]


PAGER_LABEL = re.compile(r'class="pager_label">\s*Page\s+\d+\s+of\s+(?:<a[^>]*>)?\s*([\d,]+)', re.I)


def page_count(page):
    """Number of results pages: the pager's 'Page 1 of N' label, else the largest page= link, else 1."""
    m = PAGER_LABEL.search(page)
    if m:
        return num(m.group(1))
    nums = [int(n) for n in PAGER.findall(page)]
    return max(nums + [1])


def last_slot(ranks):
    """Last rank slot covered by a page: the last rank plus the other entries tied at it."""
    r = ranks[-1]
    return r + ranks.count(r) - 1


def count_jam(ranks_first, ranks_last, pages, carry=0):
    """N0, L and V for one jam, plus the top region (slots on results page 1) and the bottom region
    (slots on the last page, after any tie group carried over from the page before). carry is the
    number of entries on the page before the last that share the last page's final rank (only
    needed when the whole last page is one tie group)."""
    if not ranks_first:
        return {"status": "no_ranks"}
    if pages > 1 and not ranks_last:
        return {"status": "last_page_empty"}
    if pages == 1:
        ranks_last = ranks_first
    n0 = last_slot(ranks_last) + carry
    listed = PER_PAGE * (pages - 1) + len(ranks_last)
    row = {"status": "ok", "pages": pages, "n0": n0, "listed": listed, "vanished": n0 - listed,
           "page1_entries": len(ranks_first)}
    if pages > 1 and len(ranks_first) != PER_PAGE:
        row["status"] = "page_size"
    elif n0 < listed or ranks_first[0] < 1 or ranks_first != sorted(ranks_first) or ranks_last != sorted(ranks_last):
        row["status"] = "inconsistent"
    top_slots = last_slot(ranks_first) if pages > 1 else n0
    row["top_slots"], row["top_vanished"] = top_slots, top_slots - len(ranks_first)
    row["bottom_slots"] = row["bottom_vanished"] = None
    if pages > 1:
        first = ranks_last[0]
        rest = [r for r in ranks_last if r != first]
        if rest:
            slots = n0 - rest[0] + 1
            row["bottom_slots"], row["bottom_vanished"] = slots, slots - len(rest)
    return row


# ---------------------------------------------------------------- reading

class Fetcher:
    """Polite reader. Saves the first save_pages pages it reads (listing pages come first) under
    raw_dir as samples; offline= re-reads such saved pages instead of the network."""

    def __init__(self, delay, log, raw_dir=None, offline=None, save_pages=0):
        self.delay, self.log, self.raw_dir, self.offline = delay, log, raw_dir, offline
        self.save_pages = save_pages
        self.count, self.last = 0, 0.0

    @staticmethod
    def key(url):
        return re.sub(r"[^A-Za-z0-9_.-]+", "_", url.replace(BASE, ""))[:150] + ".html"

    def __call__(self, url):
        if self.offline:
            p = os.path.join(self.offline, self.key(url))
            if not os.path.exists(p):
                return 0, ""
            with open(p, encoding="utf-8") as f:
                body = f.read()
            status = int(body[:3]) if body[:3].isdigit() else 200
            return status, body[4:] if body[:3].isdigit() else body
        status, body = 0, ""
        for attempt in range(3):
            wait = self.last + self.delay - time.monotonic()
            if wait > 0:
                time.sleep(wait)
            self.last = time.monotonic()
            self.count += 1
            try:
                req = urllib.request.Request(url, headers={"User-Agent": UA})
                with urllib.request.urlopen(req, timeout=40) as r:
                    status, body = r.status, r.read().decode("utf-8", "replace")
            except urllib.error.HTTPError as e:
                status, body = e.code, ""
            except Exception as e:  # network trouble: back off and retry
                self.log("  %s on %s" % (type(e).__name__, url))
                status, body = 0, ""
            if status in (200, 404, 410):
                break
            time.sleep(10 * (attempt + 1))
        if self.raw_dir and self.count <= self.save_pages:
            os.makedirs(self.raw_dir, exist_ok=True)
            with open(os.path.join(self.raw_dir, self.key(url)), "w", encoding="utf-8") as f:
                f.write("%03d\n" % status + body)
        return status, body


def read_jam(slug, fetch):
    url = "%s/jam/%s/results" % (BASE, slug)
    status, first = fetch(url)
    row = {"slug": slug, "http": status}
    if status != 200:
        row["status"] = "http_%s" % status
        return row
    row.update(parse_header(first))
    pages = page_count(first)
    ranks_first = parse_ranks(first)
    ranks_last = ranks_first
    row["_ranks"] = {"pages": pages, "first": ranks_first, "last": None}
    if pages > 1 and ranks_first:
        status, last = fetch("%s?page=%d" % (url, pages))
        if status != 200:
            row["status"] = "last_http_%s" % status
            return row
        ranks_last = parse_ranks(last)
        row["_ranks"]["last"] = ranks_last
    carry = 0
    if pages > 1 and ranks_last and ranks_last[0] == ranks_last[-1]:
        # The whole last page is one tie group, which may have begun on the page before.
        if pages == 2:
            before = ranks_first
        else:
            status, prev = fetch("%s?page=%d" % (url, pages - 1))
            if status != 200:
                row["status"] = "prev_http_%s" % status
                return row
            before = parse_ranks(prev)
        carry = before.count(ranks_last[-1])
        row["_ranks"]["carry"] = carry
        if before and before[0] == ranks_last[-1]:
            row.update(count_jam(ranks_first, ranks_last, pages, carry))
            row["status"] = "tie_span"
            return row
    row.update(count_jam(ranks_first, ranks_last, pages, carry))
    return row


# ---------------------------------------------------------------- analysis

def parse_time(s):
    return dt.datetime.strptime(s, "%Y-%m-%d %H:%M:%S")


def age_years(sub_end, read_at):
    return (parse_time(read_at) - parse_time(sub_end)).total_seconds() / (365.25 * 86400)


COHORTS = [("lt1", 0, 1), ("1to2", 1, 2), ("2to3", 2, 3), ("3to5", 3, 5), ("ge5", 5, 99)]


def eligible(rows):
    return [r for r in rows if r.get("status") == "ok" and r.get("sub_end") and r["sub_end"] <= LAST_END
            and r["n0"] >= MIN_N0]


def pooled(rows, v="vanished", n="n0"):
    den = sum(r[n] for r in rows)
    return sum(r[v] for r in rows) / den if den else None


def boot(rows, stat, iters, seed):
    """95% percentile interval of stat(rows) when jams are resampled with replacement."""
    if not rows:
        return None
    rng = random.Random(seed)
    vals = []
    for _ in range(iters):
        s = stat([rows[rng.randrange(len(rows))] for _ in rows])
        if s is not None:
            vals.append(s)
    vals.sort()
    if not vals:
        return None
    return [round(vals[int(0.025 * (len(vals) - 1))], 4), round(vals[int(0.975 * (len(vals) - 1))], 4)]


def boot_diff(a, b, stat, iters, seed):
    """95% interval of stat(a) - stat(b), each group resampled on its own."""
    if not a or not b:
        return None
    rng = random.Random(seed)
    vals = []
    for _ in range(iters):
        sa = stat([a[rng.randrange(len(a))] for _ in a])
        sb = stat([b[rng.randrange(len(b))] for _ in b])
        if sa is not None and sb is not None:
            vals.append(sa - sb)
    vals.sort()
    return [round(vals[int(0.025 * (len(vals) - 1))], 4), round(vals[int(0.975 * (len(vals) - 1))], 4)]


def ranks_of(xs):
    """Average ranks (1-based), ties sharing the mean rank."""
    order = sorted(range(len(xs)), key=lambda i: xs[i])
    out = [0.0] * len(xs)
    i = 0
    while i < len(order):
        j = i
        while j + 1 < len(order) and xs[order[j + 1]] == xs[order[i]]:
            j += 1
        for k in range(i, j + 1):
            out[order[k]] = (i + j) / 2 + 1
        i = j + 1
    return out


def pearson(xs, ys):
    n = len(xs)
    mx, my = sum(xs) / n, sum(ys) / n
    sxy = sum((x - mx) * (y - my) for x, y in zip(xs, ys))
    sxx = sum((x - mx) ** 2 for x in xs)
    syy = sum((y - my) ** 2 for y in ys)
    return sxy / math.sqrt(sxx * syy) if sxx and syy else 0.0


def spearman(xs, ys, perms, seed):
    """Spearman's rho and its one-sided permutation p-value (rho at least this large)."""
    rx, ry = ranks_of(xs), ranks_of(ys)
    rho = pearson(rx, ry)
    rng = random.Random(seed)
    ry2 = list(ry)
    hits = 0
    for _ in range(perms):
        rng.shuffle(ry2)
        if pearson(rx, ry2) >= rho - 1e-12:
            hits += 1
    return round(rho, 4), round((hits + 1) / (perms + 1), 4)


def wilson(k, n, z=1.959964):
    if not n:
        return None
    p = k / n
    d = 1 + z * z / n
    c = (p + z * z / (2 * n)) / d
    h = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / d
    return [round(c - h, 4), round(c + h, 4)]


def r4(x):
    return None if x is None else round(x, 4)


def analyse(rows, read_at, iters=2000, seed=20261101):
    s = {"version": VERSION, "read_at_utc": read_at, "frame_jams": len(rows)}
    st = {}
    for r in rows:
        st[r.get("status", "?")] = st.get(r.get("status", "?"), 0) + 1
    s["status_counts"] = dict(sorted(st.items()))
    fetched = [r for r in rows if r.get("http") == 200]
    bad = [r for r in fetched if r.get("status") in ("inconsistent", "page_size", "last_page_empty")
           or (r.get("status") == "ok" and not r.get("sub_end"))]
    s["reader_check"] = {"results_pages_read": len(fetched), "unusable": len(bad),
                         "unusable_share": r4(len(bad) / len(fetched)) if fetched else None}
    el = eligible(rows)
    for r in el:
        r["age"] = age_years(r["sub_end"], read_at)
    s["eligible_jams"] = len(el)
    s["eligible_entries_n0"] = sum(r["n0"] for r in el)
    s["eligible_vanished"] = sum(r["vanished"] for r in el)
    over = [r for r in el if r.get("rated") is not None and r["n0"] > r["rated"] + 2]
    s["reader_check"]["n0_above_rated"] = len(over)
    s["overall"] = {"pooled": r4(pooled(el)), "ci95": boot(el, pooled, iters, seed)}
    s["cohorts"] = {}
    groups = {}
    for name, lo, hi in COHORTS:
        g = [r for r in el if lo <= r["age"] < hi]
        groups[name] = g
        shares = sorted(r["vanished"] / r["n0"] for r in g)
        s["cohorts"][name] = {
            "jams": len(g), "n0": sum(r["n0"] for r in g), "vanished": sum(r["vanished"] for r in g),
            "pooled": r4(pooled(g)), "ci95": boot(g, pooled, iters, seed),
            "median_jam_share": r4(shares[len(shares) // 2]) if shares else None,
            "jams_with_any_vanished": sum(1 for r in g if r["vanished"] >= 1),
            "live_count_below_rated": sum(1 for r in g if r.get("rated") is not None
                                          and r.get("submitted") is not None and r["submitted"] < r["rated"])}
    lt2 = groups["lt1"] + groups["1to2"]
    s["p1_diff_ge5_minus_lt2"] = {"diff": r4(pooled(groups["ge5"]) - pooled(lt2))
                                  if groups["ge5"] and lt2 else None,
                                  "ci95": boot_diff(groups["ge5"], lt2, pooled, iters, seed)}
    big = [r for r in el if r["n0"] >= 30]
    if len(big) >= 3:
        rho, p = spearman([r["age"] for r in big], [r["vanished"] / r["n0"] for r in big], iters, seed)
    else:
        rho, p = None, None
    s["p4_spearman_age_share"] = {"jams": len(big), "rho": rho, "p_one_sided": p}
    old = groups["ge5"]
    k = sum(1 for r in old if r["vanished"] >= 1)
    s["p5_old_jams_any_vanished"] = {"k": k, "n": len(old), "share": r4(k / len(old)) if old else None,
                                     "wilson95": wilson(k, len(old))}
    tb = [r for r in el if r["age"] >= 2 and r["pages"] >= 3 and r.get("bottom_slots")]

    def bottom_minus_top(rs):
        b = pooled(rs, "bottom_vanished", "bottom_slots")
        t = pooled(rs, "top_vanished", "top_slots")
        return None if b is None or t is None else b - t
    s["p6_bottom_vs_top"] = {"jams": len(tb), "bottom": r4(pooled(tb, "bottom_vanished", "bottom_slots")),
                             "top": r4(pooled(tb, "top_vanished", "top_slots")),
                             "diff": r4(bottom_minus_top(tb)) if tb else None,
                             "ci95": boot(tb, bottom_minus_top, iters, seed)}
    # Exploratory: one constant yearly rate, from pooled share = 1 - exp(-rate x age) fitted by
    # least squares over the eligible jams' shares weighted by N0 (grid search).
    best = None
    for i in range(1, 2001):
        lam = i / 10000.0
        sse = sum(r["n0"] * (r["vanished"] / r["n0"] - (1 - math.exp(-lam * r["age"]))) ** 2 for r in el)
        if best is None or sse < best[1]:
            best = (lam, sse)
    s["exploratory_yearly_rate"] = round(best[0], 4) if best and el else None
    s["grades"] = grade(s)
    return s


def grade(s):
    """Grades exactly as written in PREREGISTRATION.md."""
    g = {}
    rc = s["reader_check"]
    reader_ok = rc["unusable_share"] is not None and rc["unusable_share"] <= 0.10
    c = s["cohorts"]

    def enough(*names):
        return reader_ok and all(c[n]["jams"] >= 30 for n in names)
    d = s["p1_diff_ge5_minus_lt2"]
    if not (reader_ok and c["ge5"]["jams"] >= 30 and c["lt1"]["jams"] + c["1to2"]["jams"] >= 30) or d["ci95"] is None:
        g["P1"] = "not graded"
    else:
        g["P1"] = "held" if d["diff"] > 0 and d["ci95"][0] > 0 else "failed"
    if not enough("ge5") or c["ge5"]["pooled"] is None:
        g["P2"] = "not graded"
    else:
        g["P2"] = "held" if 0.03 <= c["ge5"]["pooled"] <= 0.15 else "failed"
    if not enough("lt1") or c["lt1"]["pooled"] is None:
        g["P3"] = "not graded"
    else:
        g["P3"] = "held" if c["lt1"]["pooled"] < 0.03 else "failed"
    p4 = s["p4_spearman_age_share"]
    if not reader_ok or p4["jams"] < 30 or p4["rho"] is None:
        g["P4"] = "not graded"
    else:
        g["P4"] = "held" if p4["rho"] > 0.10 and p4["p_one_sided"] < 0.05 else "failed"
    p5 = s["p5_old_jams_any_vanished"]
    if not enough("ge5"):
        g["P5"] = "not graded"
    else:
        g["P5"] = "held" if p5["share"] >= 0.80 else "failed"
    p6 = s["p6_bottom_vs_top"]
    if not reader_ok or p6["jams"] < 30 or p6["ci95"] is None:
        g["P6"] = "not graded"
    else:
        g["P6"] = "held" if p6["diff"] > 0 and p6["ci95"][0] > 0 else "failed"
    return g


COLUMNS = ["slug", "http", "status", "sub_start", "sub_end", "submitted", "ratings", "rated", "rated_pct",
           "pages", "page1_entries", "n0", "listed", "vanished", "top_slots", "top_vanished", "bottom_slots",
           "bottom_vanished"]


def write_rows(rows, path):
    with open(path, "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(COLUMNS)
        for r in rows:
            w.writerow(["" if r.get(k) is None else r.get(k) for k in COLUMNS])


INTS = {"http", "submitted", "ratings", "rated", "pages", "page1_entries", "n0", "listed", "vanished",
        "top_slots", "top_vanished", "bottom_slots", "bottom_vanished"}


def read_rows(path):
    """jams.csv back into row dicts (empty cells become None), for re-analysis without the network."""
    rows = []
    with open(path, newline="", encoding="utf-8") as f:
        for rec in csv.DictReader(f):
            r = {}
            for k, v in rec.items():
                if v == "":
                    r[k] = None
                elif k in INTS:
                    r[k] = int(v)
                elif k == "rated_pct":
                    r[k] = float(v)
                else:
                    r[k] = v
            rows.append(r)
    return rows


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--out", default="out")
    ap.add_argument("--pages", type=int, default=FRAME_PAGES)
    ap.add_argument("--delay", type=float, default=1.0)
    ap.add_argument("--deadline-minutes", type=float, default=200)
    ap.add_argument("--iters", type=int, default=2000)
    ap.add_argument("--offline", default=None, help="folder of saved pages: re-parse without network")
    ap.add_argument("--read-at", default=None, help="'YYYY-MM-DD HH:MM:SS' UTC; default now (offline: required)")
    ap.add_argument("--from-csv", default=None, help="re-analyse a saved jams.csv (needs --read-at)")
    a = ap.parse_args(argv)
    if a.from_csv:
        s = analyse(read_rows(a.from_csv), a.read_at, a.iters)
        os.makedirs(a.out, exist_ok=True)
        with open(os.path.join(a.out, "summary.json"), "w", encoding="utf-8") as f:
            json.dump(s, f, indent=1)
        print(json.dumps(s["grades"]))
        return 0
    start = time.monotonic()
    deadline = start + a.deadline_minutes * 60

    def log(msg):
        print("[%6.0f s] %s" % (time.monotonic() - start, msg), flush=True)

    os.makedirs(a.out, exist_ok=True)
    raw = None if a.offline else os.path.join(a.out, "raw")
    fetch = Fetcher(a.delay, log, raw_dir=raw, offline=a.offline, save_pages=a.pages + 30)
    read_at = a.read_at or dt.datetime.now(dt.timezone.utc).strftime("%Y-%m-%d %H:%M:%S")
    listings = []
    for p in range(1, a.pages + 1):
        status, page = fetch("%s/jams/past?page=%d" % (BASE, p))
        if status != 200:
            log("listing page %d: http %s" % (p, status))
            continue
        listings.append(page)
    frame = frame_from_listings(listings)
    ranked = [slug for slug, has_results in frame if has_results]
    if frame and not ranked:
        log("WARNING: no results links found on the listing pages; reading every slug's results page")
        ranked = [slug for slug, _ in frame]
    log("frame: %d jams on %d listing pages, %d with a results link" % (len(frame), len(listings), len(ranked)))
    rows = []
    for i, slug in enumerate(ranked):
        if time.monotonic() >= deadline:
            rows.append({"slug": slug, "status": "not_fetched"})
            continue
        try:
            rows.append(read_jam(slug, fetch))
        except Exception as e:  # one odd page must not stop the run; it counts as not read
            log("  %s: %s" % (slug, type(e).__name__))
            rows.append({"slug": slug, "status": "error"})
        if i % 100 == 99:
            log("  jams read: %d of %d" % (i + 1, len(ranked)))
    # Save the rows before any analysis, so a later crash cannot lose what was read.
    write_rows(rows, os.path.join(a.out, "jams.csv"))
    with open(os.path.join(a.out, "ranks.jsonl"), "w", encoding="utf-8") as f:
        for r in rows:
            if r.get("_ranks"):
                f.write(json.dumps({"slug": r["slug"], **r["_ranks"]}) + "\n")
    with open(os.path.join(a.out, "read_at.txt"), "w", encoding="utf-8") as f:
        f.write(read_at + "\n")
    summary = analyse(rows, read_at, a.iters)
    summary["frame"] = {"listing_url": BASE + "/jams/past?page=N", "listing_pages_read": len(listings),
                        "slugs": len(frame), "with_results_link": sum(1 for _, h in frame if h),
                        "read": len(ranked)}
    summary["requests"] = fetch.count
    with open(os.path.join(a.out, "summary.json"), "w", encoding="utf-8") as f:
        json.dump(summary, f, indent=1)
    log("done: %d jams, %d requests; grades %s" % (len(rows), fetch.count, json.dumps(summary["grades"])))
    return 0


if __name__ == "__main__":
    sys.exit(main())
