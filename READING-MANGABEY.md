# READING-MANGABEY: what the graded call-order test says

Post-hoc reading of `results/mangabey_results.json` and `results/RESULTS-MANGABEY.md` (job
`mangabey-order-v1`, run 2026-11-22 11:13 UTC), graded by the rules of `MANGABEY-PREREG.md`
(registered before the data file was opened). `test_mangabey_results.py` regrades the verdict,
flags, predictions and Brier score from the stored values. MV2, Munim, Inc.
(mv2@munimtech.com). Made with AI agents; no human expert has checked it yet. Text CC BY 4.0.

## Verdict

**ORDER_EFFECT_WITHIN_CALLER**, with the registered flag **DAY_CONFOUND** (explained below).
Five of six predictions came true (Brier 0.160).

## Data that entered

- `calldatamgb.csv` from figshare 10.6084/m9.figshare.29503334 v2 (CC BY 4.0), 112,356 bytes as
  listed, 1,751 utterances from 55 callers in two groups.
- The column `call.name.unique` failed the registered anchors (73 twitter_grunt and 141
  grunt_twitter, outside 38-48 and 66-84); `call.name` passed (43 twitter_grunt from 17 callers,
  76 grunt_twitter from 26), close to the paper's 43 and 73. That column was used, by the rule.
- 15 females produced both orders; 40 of the 43 twitter_grunt utterances come from them.

## Main numbers

Score D per utterance: +1 give affiliation (GI) without feeding (FE), -1 feeding without GI,
0 otherwise. T = sum of D over twitter_grunt utterances; exact null = order labels reassigned
among each female's own bigrams.

| analysis | strata | T | null mean | p two-sided | weighted difference in D |
|---|---|---|---|---|---|
| **within female (primary)** | 15 | 20 | 7.06 | **0.0002** | 0.644 |
| caller-blind (pooled) | 1 | 20 | 3.97 | 0.0003 | 0.584 |
| within female and day | 9 | 3 | 3.00 | 1.000 | 0.000 |

- Leaving out any one of the 15 females keeps p two-sided at or below 0.0075.
- Secondary, within female (Holm over three): feeding present p 0.0014 (less often with
  twitter_grunt), give affiliation present p 0.0089, infant-directed (XI or XX) p 0.023.
  Twitter-first against grunt-first sequences of any length: p 0.0005.
- Calibration: with order labels shuffled within each female (2,000 worlds), the caller-blind
  test fired in 5.25% and the within-female test in 2.1%. Power at the larger planted shift
  (h = 0.30): 0.864.

## Reading

1. The central claim of Le Floch et al. 2026 holds up under the test it lacked. **The same
   females use twitter_grunt in affiliation and grunt_twitter while feeding**, more than their
   own bigrams would by chance, and no single female carries it. The within-female effect (0.644)
   is as large as the pooled one (0.584), so the contrast is not produced by who uses which
   order. Unlike several other headline results we have re-tested, the published-style pooled
   comparison was also well calibrated on these data (5.25% false alarms).
2. **DAY_CONFOUND, read with care.** The flag fires, as registered, because the female-by-day
   test is not significant. But that test has almost no material: only 9 twitter_grunt
   utterances fall on a day when the same female also gave a grunt_twitter, and its observed sum
   equals its null mean exactly (3 against 3.00). It neither supports nor rules out a day effect.
   What remains open: if a female's days differ (feeding days against days with a young infant),
   order and context could both follow the day rather than each other. These data cannot
   separate that; a playback or a within-day sampling design could.
3. Context is the authors' coding and stands in for meaning, as in the paper. Nothing here tests
   what listeners understand, and "order-sensitive compositionality" is the authors' term for a
   context difference; the test supports the context difference, not a semantic analysis of it.

## Limits

One population, two groups, 15 informative females; context codes and call labels from the
authors' annotation; no acoustic check of the call labels. The primary test is exact
(no random numbers); calibration and power use 2,000 and 1,000 simulated worlds. Made with AI
agents working in MV2's name; not yet checked by a human expert.
