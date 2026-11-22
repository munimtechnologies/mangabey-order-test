# RESULTS-MANGABEY: does call order change context within a caller?

Rendered by mangabey_test.py from mangabey_results.json (pre-registration MANGABEY-PREREG.md).
Made with AI agents working in MV2's name (MV2, Munim, Inc.); not yet checked by a human expert.
Data: Le Floch et al. 2026, figshare 10.6084/m9.figshare.29503334 v2 (CC BY 4.0), calldatamgb.csv.

## Verdict

**ORDER_EFFECT_WITHIN_CALLER**

Type column: call.name
Flags: DAY_CONFOUND True, ONE_CALLER_DRIVES False, POOLED_ONLY False

Females with both orders (informative callers): 15; twitter_grunt utterances 43, of which 40 from informative callers.

## Primary score D (+1 give affiliation, -1 feeding), twitter_grunt vs grunt_twitter

| analysis | strata | T (sum of D over twitter_grunt) | null mean | p two-sided | weighted difference |
|---|---|---|---|---|---|
| within caller (primary) | 15 | 20 | 7.061 | 0.0002 | 0.644 |
| caller-blind (pooled) | 1 | 20 | 3.975 | 0.0003 | 0.584 |
| within caller and day | 9 | 3 | 3.000 | 1.0000 | 0.000 |

## Secondary (within caller)

| outcome | T | null mean | p two-sided | Holm |
|---|---|---|---|---|
| FE | 4 | 10.549 | 0.0005 | 0.0014 |
| GI | 24 | 17.610 | 0.0045 | 0.0089 |
| INF | 21 | 15.943 | 0.0232 | 0.0232 |
| D, twitter-first vs grunt-first (incl. 3+ calls) | 33 | 17.951 | 0.0005 | - |

## Calibration

| world | caller-blind test fires | within-caller test fires |
|---|---|---|
| W0, order labels permuted within caller (R = 2000) | 0.052 | 0.021 |
| W1, planted shift h = 0.15 | - | 0.321 |
| W1, planted shift h = 0.30 | - | 0.864 |

Leave one caller out: 15 of 15 drops keep p two-sided <= 0.05.

## Predictions

| id | prior | outcome |
|---|---|---|
| M1 | 0.75 | True |
| M2 | 0.55 | True |
| M3 | 0.85 | True |
| M4 | 0.45 | True |
| M5 | 0.35 | False |
| M6 | 0.50 | True |

Brier score 0.160.
