# SPDX-License-Identifier: Apache-2.0
# test_mangabey_results.py: an independent regrade of the mangabey order job output
# (results/mangabey_results.json, job mangabey-order-v1, registered in MANGABEY-PREREG.md).
# Written after the result was read (2026-11-22). It re-derives from the stored values only:
# the verdict and flags (MANGABEY-PREREG.md section 5), predictions M1-M6 and the Brier score,
# and the two-sided p values from their one-sided parts. Stdlib only.
# MV2, Munim, Inc. (mv2@munimtech.com). Made with AI agents. Apache-2.0.
import json
import os
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
RES = os.path.join(HERE, "results", "mangabey_results.json")
ALPHA = 0.05
PRIORS = [("M1", 0.75), ("M2", 0.55), ("M3", 0.85), ("M4", 0.45), ("M5", 0.35), ("M6", 0.50)]


def p_two(t):
    return min(1.0, 2.0 * min(t["p_high"], t["p_low"]))


def regrade(r):
    a = r["analysis"]
    main = a["main"]
    if r.get("type_col") is None:
        verdict = "SCHEMA_UNRESOLVED"
    elif a["callers"]["informative"] < 4:
        verdict = "TOO_FEW_CALLERS"
    elif p_two(main) <= ALPHA and main["obs"] > main["mean"]:
        verdict = "ORDER_EFFECT_WITHIN_CALLER"
    elif p_two(main) <= ALPHA:
        verdict = "REVERSED_WITHIN_CALLER"
    elif a["power"]["0.30"] >= 0.80:
        verdict = "NO_WITHIN_CALLER_EFFECT_POWERED"
    else:
        verdict = "UNDERPOWERED"
    pooled = a["pooled"]
    pooled_fires = p_two(pooled) <= ALPHA and pooled["obs"] > pooled["mean"]
    win = verdict == "ORDER_EFFECT_WITHIN_CALLER"
    loo_max = max(v["p_two"] for v in a["leave_one_caller_out"].values())
    flags = {"POOLED_ONLY": pooled_fires and not win,
             "DAY_CONFOUND": win and p_two(a["caller_day"]) > ALPHA,
             "ONE_CALLER_DRIVES": win and loo_max > ALPHA}
    came = {"M1": verdict != "SCHEMA_UNRESOLVED", "M2": a["callers"]["informative"] >= 8,
            "M3": pooled_fires, "M4": win, "M5": a["W0"]["pooled_fires"] > 0.10,
            "M6": a["power"]["0.30"] >= 0.80}
    brier = sum((p - (1.0 if came[k] else 0.0)) ** 2 for k, p in PRIORS) / len(PRIORS)
    return verdict, flags, came, brier, loo_max


@unittest.skipUnless(os.path.exists(RES), "results/mangabey_results.json not present")
class TestMangabeyResults(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        with open(RES, encoding="utf-8") as f:
            cls.r = json.load(f)
        cls.v, cls.flags, cls.came, cls.brier, cls.loo_max = regrade(cls.r)

    def test_verdict_and_flags(self):
        self.assertEqual(self.v, "ORDER_EFFECT_WITHIN_CALLER")
        self.assertEqual(self.r["verdict"], self.v)
        self.assertEqual(self.r["flags"], self.flags)
        self.assertEqual(self.flags, {"POOLED_ONLY": False, "DAY_CONFOUND": True,
                                      "ONE_CALLER_DRIVES": False})
        self.assertLess(self.loo_max, 0.01)

    def test_p_two(self):
        a = self.r["analysis"]
        for k in ("main", "pooled", "caller_day"):
            self.assertAlmostEqual(a[k]["p_two"], p_two(a[k]), places=15)
        for k in ("FE", "GI", "INF", "first_call"):
            self.assertAlmostEqual(a["secondary"][k]["p_two"], p_two(a["secondary"][k]),
                                   places=15)
        self.assertLess(a["main"]["p_two"], 0.001)
        self.assertEqual((a["main"]["obs"], a["main"]["strata"], a["main"]["n_focal"]),
                         (20, 15, 40))
        # the caller x day test sits exactly on its null mean
        self.assertEqual((a["caller_day"]["obs"], a["caller_day"]["strata"]), (3, 9))
        self.assertAlmostEqual(a["caller_day"]["mean"], 3.0, places=12)

    def test_holm(self):
        s = self.r["analysis"]["secondary"]
        ps = sorted((s[k]["p_two"], k) for k in ("FE", "GI", "INF"))
        running = 0.0
        for i, (p, k) in enumerate(ps):
            running = max(running, min(1.0, (3 - i) * p))
            self.assertAlmostEqual(s[k]["p_holm"], running, places=12)

    def test_predictions_and_brier(self):
        got = {k: v["outcome"] for k, v in self.r["predictions"].items()}
        self.assertEqual(got, self.came)
        # (.0625 + .2025 + .0225 + .3025 + .1225 + .25) / 6 = .9625 / 6
        self.assertAlmostEqual(self.brier, 0.9625 / 6, places=12)
        self.assertAlmostEqual(self.r["brier"], self.brier, places=12)


if __name__ == "__main__":
    unittest.main()
