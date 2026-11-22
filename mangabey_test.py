#!/usr/bin/env python3
# Copyright 2026 MV2, Munim, Inc. Licensed under the Apache License, Version 2.0 (Apache-2.0).
# Made with AI agents working in MV2's name.
"""mangabey-order-test (MANGABEY-PREREG.md): does call ORDER change context within a caller?

Le Floch et al. (2026, BMC Biology 24:81) report that sooty mangabey females use 'twitter_grunt'
mostly in infant-directed affiliation and the reverse 'grunt_twitter' mostly while feeding, and
call this order-sensitive compositionality. Their model is a Bayesian multinomial over context
features with a caller intercept; no test asks whether the SAME female shifts context with order.
This script runs that test exactly: within each female who produced both bigrams, the order label
is exchangeable under the null, and the null distribution of the summed score is enumerated
exactly (stratified hypergeometric convolution). Standard library only.

Usage: python mangabey_test.py --data-dir /data --out-dir /out
Outputs: mangabey_results.json and RESULTS-MANGABEY.md in --out-dir.
"""
import argparse
import csv
import hashlib
import io
import json
import math
import os
import random
import re
import sys
import time
import urllib.request

DATA = {"calldatamgb.csv": "https://ndownloader.figshare.com/files/56058536",
        "readme_calldatamgb.txt": "https://ndownloader.figshare.com/files/56084786"}
EXPECTED_BYTES = 112356
UA = "MV2-Munim-research/1.0 (mv2@munimtech.com)"
SEED = 20261122
R_NULL = 2000
R_POWER = 1000
H_LEVELS = (0.15, 0.30)
ALPHA = 0.05
POWER_MIN = 0.80
MIN_CALLERS = 4
# published anchors (Le Floch et al. 2026, Results): twitter_grunt N = 43 (17 females),
# grunt_twitter N = 73 (26 females; the Methods say 76). The type column is accepted only if
# the female, context-known counts fall in these windows.
ANCHOR_TG = (38, 48)
ANCHOR_GT = (66, 84)
TYPE_COLS = ("call.name.unique", "call.name")
NA = {"", "na", "nan", "none", "null"}
PRIORS = {"M1": 0.75, "M2": 0.55, "M3": 0.85, "M4": 0.45, "M5": 0.35, "M6": 0.50}


# ---------------------------------------------------------------- parsing
def collapse(tokens):
    out = []
    for t in tokens:
        if not out or out[-1] != t:
            out.append(t)
    return out


def utype(s):
    """Utterance type from a call-name string: adjacent repeats collapsed, then
    GT / TG (exactly grunt then twitter / twitter then grunt), GTX / TGX (3+ calls, only grunt
    and twitter, by first call), G, T, or OTHER."""
    toks = [t.lower() for t in re.split(r"[_\s]+", (s or "").strip()) if t]
    c = collapse(toks)
    if c == ["grunt", "twitter"]:
        return "GT"
    if c == ["twitter", "grunt"]:
        return "TG"
    if len(c) >= 3 and set(c) <= {"grunt", "twitter"}:
        return "GTX" if c[0] == "grunt" else "TGX"
    if c == ["grunt"]:
        return "G"
    if c == ["twitter"]:
        return "T"
    return "OTHER"


def features(s):
    """Set of context feature codes (upper case), or None when the context is missing."""
    s = (s or "").strip()
    if s.lower() in NA:
        return None
    f = set(t.upper() for t in re.split(r"[_\s,;+/]+", s) if t)
    return f or None


def score(f):
    """Primary score D: +1 give affiliation (GI) without feeding (FE), -1 feeding without GI,
    0 for both or neither."""
    return (1 if "GI" in f else 0) - (1 if "FE" in f else 0)


def is_female(s):
    return (s or "").strip().lower().startswith("f")


def read_table(text):
    """csv.DictReader with the delimiter (',', ';' or tab) most common in the header line."""
    text = text.lstrip("﻿")
    first = text.splitlines()[0] if text.strip() else ""
    delim = max((",", ";", "\t"), key=lambda d: first.count(d))
    rows = list(csv.DictReader(io.StringIO(text), delimiter=delim))
    cols = [c.strip() for c in (rows[0].keys() if rows else [])]
    rows = [{(k or "").strip(): (v if isinstance(v, str) else "") for k, v in r.items()}
            for r in rows]
    return rows, delim, cols


def col(cols, name):
    for c in cols:
        if c.lower() == name.lower():
            return c
    return None


def records(rows, cols, type_col):
    c_caller, c_sex = col(cols, "caller"), col(cols, "sex")
    c_date, c_ctx = col(cols, "date"), col(cols, "context")
    out = []
    for r in rows:
        out.append({"caller": (r.get(c_caller) or "").strip(),
                    "female": is_female(r.get(c_sex)),
                    "date": (r.get(c_date) or "").strip(),
                    "type": utype(r.get(type_col)),
                    "feat": features(r.get(c_ctx))})
    return out


def anchor_counts(recs):
    out = {}
    for t in ("TG", "GT"):
        sel = [r for r in recs if r["female"] and r["feat"] is not None and r["type"] == t]
        out[t] = {"n": len(sel), "callers": len(set(r["caller"] for r in sel))}
    return out


def anchors_ok(a):
    return (ANCHOR_TG[0] <= a["TG"]["n"] <= ANCHOR_TG[1]
            and ANCHOR_GT[0] <= a["GT"]["n"] <= ANCHOR_GT[1])


def resolve(rows, cols):
    """Pick the first type column whose counts meet the anchors; also require the columns
    caller, sex, date and context, and both FE and GI among the context codes."""
    tried = {}
    need = [n for n in ("caller", "sex", "date", "context") if col(cols, n) is None]
    if need:
        return None, None, {"missing_columns": need}
    for name in TYPE_COLS:
        c = col(cols, name)
        if c is None:
            tried[name] = "absent"
            continue
        recs = records(rows, cols, c)
        a = anchor_counts(recs)
        tried[name] = a
        codes = set()
        for r in recs:
            if r["feat"]:
                codes |= r["feat"]
        if anchors_ok(a) and "FE" in codes and "GI" in codes:
            return c, recs, tried
    return None, None, tried


# ---------------------------------------------------------------- exact stratified test
def stratum_dist(vals, k):
    """Distribution {sum: prob} of the sum of a uniformly random k-subset of vals (each -1, 0
    or +1)."""
    a = sum(1 for v in vals if v == 1)
    c = sum(1 for v in vals if v == -1)
    n = len(vals)
    b = n - a - c
    tot = math.comb(n, k)
    dist = {}
    for x in range(0, min(a, k) + 1):
        for z in range(0, min(c, k - x) + 1):
            y = k - x - z
            if y > b:
                continue
            p = math.comb(a, x) * math.comb(b, y) * math.comb(c, z) / tot
            dist[x - z] = dist.get(x - z, 0.0) + p
    return dist


def convolve(d1, d2):
    out = {}
    for s1, p1 in d1.items():
        for s2, p2 in d2.items():
            out[s1 + s2] = out.get(s1 + s2, 0.0) + p1 * p2
    return out


def exact_test(strata):
    """strata: list of (vals, labels), labels True = the focal order (twitter first).
    Only strata with both labels count. T = sum of vals over focal-labelled items."""
    dist = {0: 1.0}
    obs = 0
    n_inf = 0
    n_focal = 0
    mh_num = 0.0
    mh_den = 0.0
    for vals, lab in strata:
        n = len(vals)
        k = sum(1 for l in lab if l)
        if k == 0 or k == n:
            continue
        n_inf += 1
        n_focal += k
        s1 = sum(v for v, l in zip(vals, lab) if l)
        s0 = sum(v for v, l in zip(vals, lab) if not l)
        obs += s1
        w = k * (n - k) / n
        mh_num += w * (s1 / k - s0 / (n - k))
        mh_den += w
        dist = convolve(dist, stratum_dist(vals, k))
    if n_inf == 0:
        return {"strata": 0, "n_focal": 0, "obs": 0, "mean": 0.0, "p_high": 1.0, "p_low": 1.0,
                "p_two": 1.0, "mh_diff": None}
    hi = min(1.0, sum(p for s, p in dist.items() if s >= obs))
    lo = min(1.0, sum(p for s, p in dist.items() if s <= obs))
    mean = sum(s * p for s, p in dist.items())
    return {"strata": n_inf, "n_focal": n_focal, "obs": obs, "mean": mean, "p_high": hi,
            "p_low": lo, "p_two": min(1.0, 2.0 * min(hi, lo)), "mh_diff": mh_num / mh_den}


def build_strata(recs, key, value, focal=("TG",), other=("GT",)):
    """Group female, context-known records of the focal and other types by key(r)."""
    groups = {}
    for r in recs:
        if not r["female"] or r["feat"] is None or r["type"] not in focal + other:
            continue
        g = groups.setdefault(key(r), ([], []))
        g[0].append(value(r["feat"]))
        g[1].append(r["type"] in focal)
    return groups


def by_caller(r):
    return r["caller"]


def by_caller_day(r):
    return r["caller"] + "|" + r["date"]


def pooled(r):
    return "all"


# ---------------------------------------------------------------- worlds
def permute_within(groups, rng):
    """W0: the order labels permuted within each stratum (no order effect by construction)."""
    out = {}
    for g, (vals, lab) in groups.items():
        lab2 = list(lab)
        rng.shuffle(lab2)
        out[g] = (list(vals), lab2)
    return out


def plant(groups, rng, h):
    """W1(h): after W0, each focal item with D != +1 becomes +1 with probability h and each
    other item with D != -1 becomes -1 with probability h."""
    out = {}
    for g, (vals, lab) in groups.items():
        v2 = []
        for v, l in zip(vals, lab):
            if l and v != 1 and rng.random() < h:
                v = 1
            elif (not l) and v != -1 and rng.random() < h:
                v = -1
            v2.append(v)
        out[g] = (v2, list(lab))
    return out


def regroup_pooled(groups):
    vals, lab = [], []
    for v, l in groups.values():
        vals += v
        lab += l
    return [(vals, lab)]


# ---------------------------------------------------------------- verdict
def verdict(schema_ok, n_callers, p_two, obs, mean, power30):
    if not schema_ok:
        return "SCHEMA_UNRESOLVED"
    if n_callers < MIN_CALLERS:
        return "TOO_FEW_CALLERS"
    if p_two <= ALPHA and obs > mean:
        return "ORDER_EFFECT_WITHIN_CALLER"
    if p_two <= ALPHA and obs < mean:
        return "REVERSED_WITHIN_CALLER"
    if power30 >= POWER_MIN:
        return "NO_WITHIN_CALLER_EFFECT_POWERED"
    return "UNDERPOWERED"


def holm(ps):
    """Holm-adjusted p values, same order as ps."""
    idx = sorted(range(len(ps)), key=lambda i: ps[i])
    out = [0.0] * len(ps)
    run_max = 0.0
    for rank, i in enumerate(idx):
        run_max = max(run_max, min(1.0, (len(ps) - rank) * ps[i]))
        out[i] = run_max
    return out


def analyse(recs, R0=R_NULL, R1=R_POWER, seed=SEED, log=print):
    rng = random.Random(seed)
    res = {}
    gc = build_strata(recs, by_caller, score)
    main = exact_test(list(gc.values()))
    res["main"] = main
    inf_callers = sorted(g for g, (v, l) in gc.items() if 0 < sum(l) < len(l))
    tg_total = sum(sum(l) for v, l in gc.values())
    res["callers"] = {"informative": len(inf_callers), "with_TG": sum(1 for v, l in gc.values() if any(l)),
                      "with_GT": sum(1 for v, l in gc.values() if not all(l)),
                      "TG_total": tg_total, "TG_in_informative": main["n_focal"]}
    pool = exact_test(list(build_strata(recs, pooled, score).values()))
    res["pooled"] = pool
    res["caller_day"] = exact_test(list(build_strata(recs, by_caller_day, score).values()))
    log("main (within caller): T %d E %.3f p_two %.4f mh %.3f; strata %d; pooled p_two %.4f" % (
        main["obs"], main["mean"], main["p_two"], main["mh_diff"] or 0.0, main["strata"],
        pool["p_two"]))
    loo = {}
    for c in inf_callers:
        t = exact_test([gc[g] for g in gc if g != c])
        loo[c] = {"p_two": t["p_two"], "obs_minus_mean": t["obs"] - t["mean"]}
    res["leave_one_caller_out"] = loo
    sec = {}
    for name, fn in (("FE", lambda f: 1 if "FE" in f else 0),
                     ("GI", lambda f: 1 if "GI" in f else 0),
                     ("INF", lambda f: 1 if ("XI" in f or "XX" in f) else 0)):
        sec[name] = exact_test(list(build_strata(recs, by_caller, fn).values()))
    adj = holm([sec[k]["p_two"] for k in ("FE", "GI", "INF")])
    for k, a in zip(("FE", "GI", "INF"), adj):
        sec[k]["p_holm"] = a
    sec["first_call"] = exact_test(list(build_strata(recs, by_caller, score, focal=("TG", "TGX"),
                                                     other=("GT", "GTX")).values()))
    res["secondary"] = sec
    # W0: how often the caller-blind (pooled) test and the within-caller test fire
    t0 = time.time()
    fp = fw = 0
    for _ in range(R0):
        w = permute_within(gc, rng)
        fp += int(exact_test(regroup_pooled(w))["p_two"] <= ALPHA)
        fw += int(exact_test(list(w.values()))["p_two"] <= ALPHA)
    res["W0"] = {"R": R0, "pooled_fires": fp / R0, "within_fires": fw / R0}
    log("W0: pooled fires %.3f within fires %.3f (%.0fs)" % (fp / R0, fw / R0, time.time() - t0))
    power = {}
    for h in H_LEVELS:
        t0 = time.time()
        hit = 0
        for _ in range(R1):
            w = plant(permute_within(gc, rng), rng, h)
            t = exact_test(list(w.values()))
            hit += int(t["p_two"] <= ALPHA and t["obs"] > t["mean"])
        power["%.2f" % h] = hit / R1
        log("W1 h=%.2f: power %.3f (%.0fs)" % (h, hit / R1, time.time() - t0))
    res["power"] = power
    return res


def grade(schema_ok, res):
    if not schema_ok:
        out = {"M1": False}
        v = verdict(False, 0, 1.0, 0, 0.0, 0.0)
        flags = {}
    else:
        m, pool = res["main"], res["pooled"]
        n_c = res["callers"]["informative"]
        p30 = res["power"]["0.30"]
        v = verdict(True, n_c, m["p_two"], m["obs"], m["mean"], p30)
        out = {"M1": True,
               "M2": n_c >= 8,
               "M3": pool["p_two"] <= ALPHA and pool["obs"] > pool["mean"],
               "M4": v == "ORDER_EFFECT_WITHIN_CALLER",
               "M5": res["W0"]["pooled_fires"] > 0.10,
               "M6": p30 >= POWER_MIN}
        loo_bad = any(x["p_two"] > ALPHA for x in res["leave_one_caller_out"].values())
        cd = res["caller_day"]
        flags = {"POOLED_ONLY": bool(out["M3"] and v != "ORDER_EFFECT_WITHIN_CALLER"),
                 "DAY_CONFOUND": bool(v == "ORDER_EFFECT_WITHIN_CALLER" and cd["p_two"] > ALPHA),
                 "ONE_CALLER_DRIVES": bool(v == "ORDER_EFFECT_WITHIN_CALLER" and loo_bad)}
    preds = {q: {"prior": PRIORS[q], "outcome": bool(out[q])} for q in sorted(out)}
    brier = sum((PRIORS[q] - (1.0 if out[q] else 0.0)) ** 2 for q in out) / len(out)
    return v, flags, preds, brier


# ---------------------------------------------------------------- description (schema only)
def describe(rows, cols, delim):
    """Column names, row count, and marginal value counts only (never type x context)."""
    d = {"columns": cols, "delimiter": delim, "rows": len(rows)}
    for name in ("sex", "group", "call.name.unique", "call.name"):
        c = col(cols, name)
        if c is None:
            continue
        cnt = {}
        for r in rows:
            k = (r.get(c) or "").strip()
            cnt[k] = cnt.get(k, 0) + 1
        top = sorted(cnt.items(), key=lambda t: (-t[1], t[0]))[:40]
        d["values_" + name] = {"distinct": len(cnt), "top": [[k, n] for k, n in top]}
    c = col(cols, "context")
    if c is not None:
        cnt = {}
        missing = 0
        for r in rows:
            f = features(r.get(c))
            if f is None:
                missing += 1
                continue
            for t in f:
                cnt[t] = cnt.get(t, 0) + 1
        d["context_codes"] = {"missing": missing,
                              "counts": [[k, n] for k, n in sorted(cnt.items(), key=lambda t: (-t[1], t[0]))]}
    c = col(cols, "caller")
    if c is not None:
        d["callers"] = len(set((r.get(c) or "").strip() for r in rows))
    return d


# ---------------------------------------------------------------- output
def fmt(x, spec="%.4f"):
    return "n/a" if x is None else spec % x


def render(res):
    L = ["# RESULTS-MANGABEY: does call order change context within a caller?", "",
         "Rendered by mangabey_test.py from mangabey_results.json (pre-registration MANGABEY-PREREG.md).",
         "Made with AI agents working in MV2's name (MV2, Munim, Inc.); not yet checked by a human expert.",
         "Data: Le Floch et al. 2026, figshare 10.6084/m9.figshare.29503334 v2 (CC BY 4.0), calldatamgb.csv.",
         "", "## Verdict", "", "**%s**" % res["verdict"], ""]
    L.append("Type column: %s" % res.get("type_col"))
    if res.get("flags"):
        L.append("Flags: " + ", ".join("%s %s" % (k, v) for k, v in sorted(res["flags"].items())))
    a = res.get("analysis")
    if a:
        m, p, cd = a["main"], a["pooled"], a["caller_day"]
        c = a["callers"]
        L += ["", "Females with both orders (informative callers): %d; twitter_grunt utterances %d, of which %d from informative callers." % (
            c["informative"], c["TG_total"], c["TG_in_informative"]), "",
            "## Primary score D (+1 give affiliation, -1 feeding), twitter_grunt vs grunt_twitter", "",
            "| analysis | strata | T (sum of D over twitter_grunt) | null mean | p two-sided | weighted difference |",
            "|---|---|---|---|---|---|"]
        for label, t in (("within caller (primary)", m), ("caller-blind (pooled)", p),
                         ("within caller and day", cd)):
            L.append("| %s | %d | %d | %.3f | %.4f | %s |" % (label, t["strata"], t["obs"], t["mean"],
                                                           t["p_two"], fmt(t["mh_diff"], "%.3f")))
        L += ["", "## Secondary (within caller)", "",
              "| outcome | T | null mean | p two-sided | Holm |", "|---|---|---|---|---|"]
        for k in ("FE", "GI", "INF"):
            t = a["secondary"][k]
            L.append("| %s | %d | %.3f | %.4f | %.4f |" % (k, t["obs"], t["mean"], t["p_two"], t["p_holm"]))
        t = a["secondary"]["first_call"]
        L.append("| D, twitter-first vs grunt-first (incl. 3+ calls) | %d | %.3f | %.4f | - |" % (
            t["obs"], t["mean"], t["p_two"]))
        L += ["", "## Calibration", "",
              "| world | caller-blind test fires | within-caller test fires |", "|---|---|---|",
              "| W0, order labels permuted within caller (R = %d) | %.3f | %.3f |" % (
                  a["W0"]["R"], a["W0"]["pooled_fires"], a["W0"]["within_fires"])]
        for h, pw in sorted(a["power"].items()):
            L.append("| W1, planted shift h = %s | - | %.3f |" % (h, pw))
        L += ["", "Leave one caller out: %d of %d drops keep p two-sided <= 0.05." % (
            sum(1 for x in a["leave_one_caller_out"].values() if x["p_two"] <= ALPHA),
            len(a["leave_one_caller_out"]))]
    L += ["", "## Predictions", "", "| id | prior | outcome |", "|---|---|---|"]
    for q in sorted(res["predictions"]):
        x = res["predictions"][q]
        L.append("| %s | %.2f | %s |" % (q, x["prior"], x["outcome"]))
    L += ["", "Brier score %.3f." % res["brier"], ""]
    return "\n".join(L)


def fetch(data_dir):
    os.makedirs(data_dir, exist_ok=True)
    info = {}
    for name, url in DATA.items():
        path = os.path.join(data_dir, name)
        if not os.path.exists(path) or os.path.getsize(path) == 0:
            req = urllib.request.Request(url, headers={"User-Agent": UA})
            with urllib.request.urlopen(req, timeout=120) as r:
                blob = r.read()
            with open(path, "wb") as fh:
                fh.write(blob)
        with open(path, "rb") as fh:
            blob = fh.read()
        info[name] = {"url": url, "sha256": hashlib.sha256(blob).hexdigest(), "bytes": len(blob)}
    return info


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--data-dir", required=True)
    ap.add_argument("--out-dir", required=True)
    a = ap.parse_args(argv)
    os.makedirs(a.out_dir, exist_ok=True)
    info = fetch(a.data_dir)
    print(json.dumps(info), flush=True)
    with open(os.path.join(a.data_dir, "readme_calldatamgb.txt"), "rb") as fh:
        print("readme:\n" + fh.read().decode("utf-8", "replace"), flush=True)
    with open(os.path.join(a.data_dir, "calldatamgb.csv"), "rb") as fh:
        text = fh.read().decode("utf-8", "replace")
    rows, cols, delim = None, None, None
    rows, delim, cols = read_table(text)
    desc = describe(rows, cols, delim)
    print("schema: " + json.dumps(desc), flush=True)
    type_col, recs, tried = resolve(rows, cols)
    print("anchors: " + json.dumps(tried), flush=True)
    res = {"data": info, "size_as_published": info["calldatamgb.csv"]["bytes"] == EXPECTED_BYTES,
           "schema": desc, "anchors": tried, "type_col": type_col,
           "settings": {"seed": SEED, "R_null": R_NULL, "R_power": R_POWER, "h": list(H_LEVELS)}}
    t0 = time.time()
    if type_col is not None:
        res["analysis"] = analyse(recs, log=lambda s: print(s, flush=True))
    v, flags, preds, brier = grade(type_col is not None, res.get("analysis"))
    res.update(verdict=v, flags=flags, predictions=preds, brier=brier,
               seconds=round(time.time() - t0, 1))
    with open(os.path.join(a.out_dir, "mangabey_results.json"), "w", encoding="utf-8") as fh:
        fh.write(json.dumps(res, indent=1, sort_keys=True))
    with open(os.path.join(a.out_dir, "RESULTS-MANGABEY.md"), "w", encoding="utf-8") as fh:
        fh.write(render(res))
    print(json.dumps({"verdict": v, "flags": flags, "brier": brier}), flush=True)
    return 0


if __name__ == "__main__":
    sys.exit(main())
