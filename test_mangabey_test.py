# SPDX-License-Identifier: Apache-2.0
# test_mangabey_test.py: unit tests for mangabey_test.py (MANGABEY-PREREG.md). Every expected
# value is worked out by hand in the comments. Standard library only; no data file is read.
# MV2, Munim, Inc. (mv2@munimtech.com). Made with AI agents. Apache-2.0.
import random
import unittest

import mangabey_test as m


def rec(caller, typ, feat, female=True, date="d1"):
    return {"caller": caller, "female": female, "date": date, "type": typ,
            "feat": None if feat is None else set(feat)}


class Parsing(unittest.TestCase):
    def test_utype(self):
        self.assertEqual(m.utype("grunt_twitter"), "GT")
        self.assertEqual(m.utype("twitter_grunt"), "TG")
        self.assertEqual(m.utype("grunt_grunt_twitter"), "GT")  # adjacent repeats collapse
        self.assertEqual(m.utype(" Twitter_Grunt "), "TG")
        self.assertEqual(m.utype("grunt_twitter_grunt"), "GTX")
        self.assertEqual(m.utype("twitter_grunt_twitter"), "TGX")
        self.assertEqual(m.utype("grunt"), "G")
        self.assertEqual(m.utype("twitter_twitter"), "T")
        self.assertEqual(m.utype("grunt_shrill"), "OTHER")
        self.assertEqual(m.utype("grunt_twitterX"), "OTHER")
        self.assertEqual(m.utype(""), "OTHER")
        self.assertEqual(m.utype(None), "OTHER")

    def test_features_and_score(self):
        self.assertEqual(m.features("GI_XI"), {"GI", "XI"})
        self.assertEqual(m.features("fe"), {"FE"})
        self.assertIsNone(m.features("NA"))
        self.assertIsNone(m.features(""))
        self.assertIsNone(m.features(None))
        self.assertEqual(m.score({"GI", "XI"}), 1)
        self.assertEqual(m.score({"FE"}), -1)
        self.assertEqual(m.score({"FE", "GI"}), 0)
        self.assertEqual(m.score({"RE"}), 0)
        self.assertTrue(m.is_female("F"))
        self.assertTrue(m.is_female("female"))
        self.assertFalse(m.is_female("M"))
        self.assertFalse(m.is_female(None))

    def test_read_table(self):
        rows, delim, cols = m.read_table("a;b\n1;2\n")
        self.assertEqual((delim, cols, rows), (";", ["a", "b"], [{"a": "1", "b": "2"}]))
        rows, delim, cols = m.read_table("﻿a,b\n1,2\n")
        self.assertEqual((delim, cols, rows), (",", ["a", "b"], [{"a": "1", "b": "2"}]))
        self.assertEqual(m.col(["Caller", "x"], "caller"), "Caller")
        self.assertIsNone(m.col(["x"], "caller"))


def table(n_tg, n_gt, unique_ok=True):
    """Synthetic file: n_tg female twitter_grunt and n_gt female grunt_twitter rows (context GI
    and FE), plus 5 male rows and 5 female rows without context. If not unique_ok, the
    call.name.unique column holds pooled labels that do not parse, so call.name must be used."""
    head = "date,group,caller,sex,call.name.unique,call.name,context\n"
    lines = []
    for i in range(n_tg):
        lines.append("d1,TMP,F%d,F,%s,twitter_grunt,GI_XI" % (i % 5, "twitter_grunt" if unique_ok else "tgX"))
    for i in range(n_gt):
        lines.append("d1,TMP,F%d,F,%s,grunt_grunt_twitter,FE" % (i % 5, "grunt_twitter" if unique_ok else "gtX"))
    for i in range(5):
        lines.append("d1,TMP,M%d,M,twitter_grunt,twitter_grunt,GI" % i)
        lines.append("d1,TMP,F%d,F,twitter_grunt,twitter_grunt,NA" % i)
    return head + "\n".join(lines) + "\n"


class Resolve(unittest.TestCase):
    def test_unique_column(self):
        # 40 TG and 70 GT female context-known rows: inside the windows (38-48, 66-84).
        # The 5 male and 5 no-context TG rows are not counted.
        rows, delim, cols = m.read_table(table(40, 70))
        c, recs, tried = m.resolve(rows, cols)
        self.assertEqual(c, "call.name.unique")
        self.assertEqual(tried["call.name.unique"], {"TG": {"n": 40, "callers": 5},
                                                      "GT": {"n": 70, "callers": 5}})
        self.assertEqual(len(recs), 120)

    def test_fallback_and_failure(self):
        rows, delim, cols = m.read_table(table(40, 70, unique_ok=False))
        c, recs, tried = m.resolve(rows, cols)
        self.assertEqual(c, "call.name")  # unique column parses to OTHER -> anchors fail
        self.assertEqual(tried["call.name.unique"]["TG"]["n"], 5 * 0)
        rows, delim, cols = m.read_table(table(20, 70))
        c, recs, tried = m.resolve(rows, cols)
        self.assertIsNone(c)  # 20 TG is outside 38-48 in both columns
        rows, delim, cols = m.read_table("date,caller,context\nd1,F1,FE\n")
        c, recs, tried = m.resolve(rows, cols)
        self.assertIsNone(c)
        self.assertEqual(tried, {"missing_columns": ["sex"]})


class Exact(unittest.TestCase):
    def test_stratum_dist(self):
        # [1, 0, -1], k = 1: each value with probability 1/3.
        d = m.stratum_dist([1, 0, -1], 1)
        self.assertEqual(sorted(d), [-1, 0, 1])
        for s in d:
            self.assertAlmostEqual(d[s], 1 / 3, places=12)
        # [1, 1, 0, 0], k = 2: sum 0 (1/6), 1 (4/6), 2 (1/6).
        d = m.stratum_dist([1, 1, 0, 0], 2)
        self.assertAlmostEqual(d[0], 1 / 6, places=12)
        self.assertAlmostEqual(d[1], 4 / 6, places=12)
        self.assertAlmostEqual(d[2], 1 / 6, places=12)

    def test_one_stratum(self):
        # focal items both +1: T = 2; null {0: 1/6, 1: 2/3, 2: 1/6}; p_high 1/6, p_low 1,
        # p_two 1/3, mean 1; weight 2*2/4 = 1, difference 2/2 - 0/2 = 1.
        t = m.exact_test([([1, 1, 0, 0], [True, True, False, False]),
                          ([1, -1], [True, True])])  # second stratum uninformative
        self.assertEqual((t["strata"], t["n_focal"], t["obs"]), (1, 2, 2))
        self.assertAlmostEqual(t["p_high"], 1 / 6, places=12)
        self.assertAlmostEqual(t["p_low"], 1.0, places=12)
        self.assertAlmostEqual(t["p_two"], 1 / 3, places=12)
        self.assertAlmostEqual(t["mean"], 1.0, places=12)
        self.assertAlmostEqual(t["mh_diff"], 1.0, places=12)

    def test_two_strata(self):
        # two strata ([1, 0], focal first): each {0: .5, 1: .5}; sum {0: .25, 1: .5, 2: .25};
        # T = 2 -> p_high .25, p_two .5.
        t = m.exact_test([([1, 0], [True, False]), ([1, 0], [True, False])])
        self.assertEqual(t["obs"], 2)
        self.assertAlmostEqual(t["p_high"], 0.25, places=12)
        self.assertAlmostEqual(t["p_two"], 0.5, places=12)
        self.assertAlmostEqual(t["mh_diff"], 1.0, places=12)
        t = m.exact_test([])
        self.assertEqual((t["strata"], t["p_two"]), (0, 1.0))

    def test_holm(self):
        # sorted 0.01, 0.03, 0.04 -> 0.03, 0.06, max(0.06, 0.04) = 0.06
        h = m.holm([0.01, 0.04, 0.03])
        self.assertAlmostEqual(h[0], 0.03, places=12)
        self.assertAlmostEqual(h[1], 0.06, places=12)
        self.assertAlmostEqual(h[2], 0.06, places=12)


class Worlds(unittest.TestCase):
    def test_permute_and_plant(self):
        g = {"A": ([1, 0, -1, 0], [True, False, False, True]), "B": ([0, 0], [True, False])}
        w = m.permute_within(g, random.Random(5))
        for k in g:
            self.assertEqual(w[k][0], g[k][0])
            self.assertEqual(sorted(w[k][1]), sorted(g[k][1]))
        p = m.plant(g, random.Random(5), 1.0)
        self.assertEqual(p["A"][0], [1, -1, -1, 1])
        self.assertEqual(p["B"][0], [1, -1])
        p = m.plant(g, random.Random(5), 0.0)
        self.assertEqual(p["A"][0], g["A"][0])


class Verdict(unittest.TestCase):
    def test_rules(self):
        v = m.verdict
        self.assertEqual(v(False, 9, 0.0, 5, 0.0, 1.0), "SCHEMA_UNRESOLVED")
        self.assertEqual(v(True, 3, 0.0, 5, 0.0, 1.0), "TOO_FEW_CALLERS")
        self.assertEqual(v(True, 4, 0.05, 5, 0.0, 0.0), "ORDER_EFFECT_WITHIN_CALLER")
        self.assertEqual(v(True, 4, 0.05, -5, 0.0, 0.0), "REVERSED_WITHIN_CALLER")
        self.assertEqual(v(True, 4, 0.051, 5, 0.0, 0.80), "NO_WITHIN_CALLER_EFFECT_POWERED")
        self.assertEqual(v(True, 4, 0.051, 5, 0.0, 0.799), "UNDERPOWERED")

    def test_grade_schema_failure(self):
        verdict, flags, preds, brier = m.grade(False, None)
        self.assertEqual(verdict, "SCHEMA_UNRESOLVED")
        self.assertEqual(preds, {"M1": {"prior": 0.75, "outcome": False}})
        self.assertAlmostEqual(brier, 0.5625, places=12)


class EndToEnd(unittest.TestCase):
    def test_within_caller_effect(self):
        # 6 females, each 4 twitter_grunt with GI (+1) and 6 grunt_twitter with FE (-1).
        # Per caller: k = 4 of 10, all four +1 -> P = 1 / C(10, 4) = 1/210; T = 24;
        # mean per caller 4 * (4 - 6)/10 = -0.8 -> -4.8. p_high = 210^-6.
        recs = []
        for c in range(6):
            recs += [rec("F%d" % c, "TG", ["GI"])] * 4 + [rec("F%d" % c, "GT", ["FE"])] * 6
        recs += [rec("M1", "TG", ["FE"], female=False), rec("F0", "TG", None),
                 rec("F0", "G", ["FE"])]  # all ignored by the primary test
        a = m.analyse(recs, R0=10, R1=10, log=lambda s: None)
        t = a["main"]
        self.assertEqual((t["strata"], t["obs"], t["n_focal"]), (6, 24, 24))
        self.assertAlmostEqual(t["mean"], -4.8, places=9)
        self.assertAlmostEqual(t["p_high"] / (210.0 ** -6), 1.0, places=6)
        self.assertEqual(a["callers"]["informative"], 6)
        self.assertEqual(a["W0"]["within_fires"] <= 1.0, True)
        verdict, flags, preds, brier = m.grade(True, a)
        self.assertEqual(verdict, "ORDER_EFFECT_WITHIN_CALLER")
        self.assertEqual(flags, {"POOLED_ONLY": False, "DAY_CONFOUND": False,
                                 "ONE_CALLER_DRIVES": False})
        self.assertTrue(preds["M3"]["outcome"])
        self.assertFalse(preds["M2"]["outcome"])  # 6 informative callers < 8
        res = {"verdict": verdict, "flags": flags, "predictions": preds, "brier": brier,
               "type_col": "call.name.unique", "analysis": a}
        md = m.render(res)
        self.assertIn("**ORDER_EFFECT_WITHIN_CALLER**", md)
        self.assertIn("Leave one caller out: 6 of 6 drops keep p two-sided <= 0.05.", md)

    def test_caller_confound(self):
        # Callers F0-F2 only ever give twitter_grunt (GI), F3-F5 only grunt_twitter (FE): no female
        # has both orders, so the within-caller test has nothing (TOO_FEW_CALLERS), while the
        # caller-blind test fires (pooled p tiny) and fires in every W0 world (labels cannot move).
        recs = []
        for c in range(3):
            recs += [rec("F%d" % c, "TG", ["GI"])] * 4
        for c in range(3, 6):
            recs += [rec("F%d" % c, "GT", ["FE"])] * 6
        a = m.analyse(recs, R0=10, R1=10, log=lambda s: None)
        self.assertEqual(a["main"]["strata"], 0)
        self.assertLess(a["pooled"]["p_two"], 1e-6)
        self.assertEqual(a["W0"]["pooled_fires"], 1.0)
        self.assertEqual(a["W0"]["within_fires"], 0.0)
        verdict, flags, preds, brier = m.grade(True, a)
        self.assertEqual(verdict, "TOO_FEW_CALLERS")
        self.assertTrue(flags["POOLED_ONLY"])
        self.assertTrue(preds["M5"]["outcome"])


if __name__ == "__main__":
    unittest.main()
