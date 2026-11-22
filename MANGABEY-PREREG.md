# MANGABEY-PREREG: does call order change context within the same female?

Pre-registration by MV2, Munim, Inc. (mv2@munimtech.com), 2026-11-22. Made with AI agents working
in MV2's name; no human expert has checked it yet. Text CC BY 4.0, code Apache-2.0.

## 0. What we had seen before writing this

The paper's text (Le Floch, Girard-Buttoz, Neumann, Azaiez, Bande, Wittig, Zuberbuhler & Crockford
2026, BMC Biology 24:81, doi 10.1186/s12915-026-02528-4, CC BY), the figshare record listing
(10.6084/m9.figshare.29503334 v2, CC BY 4.0: calldatamgb.csv 112,356 bytes, Mangabey meaning.R,
a readme), and the column names reported for calldatamgb.csv (date, group, rec_id, utt_id, caller,
sex, call.name.unique, combi.length.unique, call.name, combi.length, context, context.length).
We have not downloaded or opened the data file or the R script. A scoop search on 2026-11-22
found no reanalysis, comment or reply.

## 1. The claim

Female sooty mangabeys in Tai National Park produce two orders of the same two calls.
'twitter_grunt' (N = 43 utterances, 17 females) is reported mostly in infant-directed and other
affiliation (give affiliation, model median 0.40, against 0.10 for feeding). 'grunt_twitter' (N = 73,
26 females) is reported mostly while feeding (0.42, against 0.22 for give affiliation). The authors
conclude "order-sensitive compositionality". The evidence is a Bayesian multinomial model over 37
context features with varying intercepts for utterance type and caller, Euclidean distances
between posterior context vectors, and the share of posterior draws in which one utterance's
proportion exceeds another's. No null model or permutation test is used.

## 2. Why a within-caller test is needed

17 females produced twitter_grunt and 26 grunt_twitter. If the females who use twitter_grunt are
mostly mothers of young infants, and those mothers spend more time in infant-directed affiliation,
the two orders will differ in context even when no female changes her context with order. A
caller intercept in a multinomial model shifts each female's overall context profile. It does
not ask the direct question: when the same female uses both orders, does twitter-first go with
affiliation and grunt-first with feeding? The exact conditional test below asks it. It uses only
the females who produced both orders, permuting the order label among each female's own bigrams.

## 3. Data and definitions (fixed before opening the file)

- File: calldatamgb.csv from figshare (files/56058536). The job prints its sha256 and size and
  whether the size equals 112,356 bytes, plus the readme text.
- Utterance type, from the call-name column: split on '_', lower case, collapse adjacent repeats.
  [grunt, twitter] is GT; [twitter, grunt] is TG; three or more calls using only grunt and
  twitter is GTX or TGX, by the first call; a lone grunt is G and a lone twitter is T; anything
  else is OTHER.
- Column choice (anchored to the paper): call.name.unique is used if, among female rows with a
  context, it gives 38-48 TG and 66-84 GT and the context codes include FE and GI. Otherwise
  call.name is tried with the same rule. If neither passes, or the columns caller, sex, date or
  context are missing, the verdict is SCHEMA_UNRESOLVED. The job then prints marginal value counts
  only (column names, the values of sex, group and the call-name columns, and context-code
  counts), never type by context, so that an amendment can fix the mapping.
- Female: sex starting with 'f' (case-insensitive). Context missing: empty, NA, NaN, None or
  null. Context codes: the context string split on '_', spaces, commas, semicolons, '+' or '/'.
- Primary score per utterance: D = +1 if GI (give affiliation) is present without FE (feeding),
  -1 if FE is present without GI, 0 otherwise.

## 4. Tests

- **Primary (within caller).** Strata: females with at least one TG and one GT (with context).
  T = sum of D over TG utterances. Null: within each stratum the TG labels are a uniformly random
  subset of that female's TG + GT utterances, of the observed size. The exact distribution is the
  convolution of per-female hypergeometric sum distributions, so no random numbers are used.
  p_two = min(1, 2 min(p_high, p_low)). The effect size is the Mantel-Haenszel-weighted difference
  in mean D (TG minus GT).
- **Caller-blind comparison (proxy for analyses that pool females):** the same exact test with all
  female TG + GT utterances in one stratum.
- **Within caller and day:** strata = female x date.
- **Leave one caller out:** the primary test without each informative female in turn.
- **Secondary (within caller, Holm over three):** FE present, GI present, and infant-directed
  (XI or XX present), each as a 0/1 score. Also D with twitter-first (TG + TGX) against grunt-first
  (GT + GTX).
- **Calibration, W0** (R = 2000, random.Random(20261122)): order labels permuted within each
  female, which by construction removes any within-female order effect. We report how often the
  caller-blind test and the within-caller test fire (p_two <= 0.05).
- **Power, W1(h)** (R = 1000 each, h = 0.15 and 0.30): W0, then each TG utterance with D != +1
  becomes +1 with probability h, and each GT utterance with D != -1 becomes -1 with probability h.
  Power = the share of worlds where the within-caller test fires in the published direction.

## 5. Verdict (applied exactly as coded in mangabey_test.py)

SCHEMA_UNRESOLVED (section 3); else TOO_FEW_CALLERS if fewer than 4 informative females; else
ORDER_EFFECT_WITHIN_CALLER if p_two <= 0.05 with T above its null mean; else
REVERSED_WITHIN_CALLER if p_two <= 0.05 with T below it; else NO_WITHIN_CALLER_EFFECT_POWERED if
W1(0.30) power >= 0.80; else UNDERPOWERED.

Flags:
- POOLED_ONLY: the caller-blind test fires in the published direction but the verdict is not
  ORDER_EFFECT_WITHIN_CALLER.
- DAY_CONFOUND: ORDER_EFFECT_WITHIN_CALLER, but the caller x day test has p_two > 0.05.
- ONE_CALLER_DRIVES: ORDER_EFFECT_WITHIN_CALLER, but some leave-one-out p_two > 0.05.

## 6. Predictions (priors) and Brier score

M1 the schema resolves with the anchors (0.75). M2 at least 8 informative females (0.55). M3 the
caller-blind test fires in the published direction (0.85). M4 the verdict is
ORDER_EFFECT_WITHIN_CALLER (0.45). M5 the caller-blind test fires in more than 10% of W0 worlds
(0.35). M6 W1(0.30) power >= 0.80 (0.50). If the schema does not resolve, only M1 is scored.

## 7. Readings fixed now

- ORDER_EFFECT_WITHIN_CALLER: the same females use twitter-first in affiliation and grunt-first
  while feeding more than their own bigrams would by chance. This is the strongest public-data
  support the order-sensitivity claim can get without playbacks. Any flag is reported with it.
- POOLED_ONLY with UNDERPOWERED or NO_WITHIN_CALLER_EFFECT_POWERED: the published contrast is
  carried by differences between females (who uses which order), not shown within females.
- TOO_FEW_CALLERS: the data cannot separate order from caller, and the claim rests on the model's
  assumptions.
- Context is the authors' coding, used as a proxy for meaning, as in the paper. Nothing here tests
  what receivers understand.

## 8. Order of work

This file, mangabey_test.py and test_mangabey_test.py are committed together, and the publish
lane runs their unit tests before the job does. The job's first step (gate.py) computes nothing
until the public copies match its own. Any later change goes into an AMENDMENT file; this file is
never edited.
