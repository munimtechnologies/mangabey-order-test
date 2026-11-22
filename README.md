# mangabey-order-test

Does call **order** change meaning in sooty mangabeys, within the same female?

Le Floch et al. (2026, *BMC Biology* 24:81) report that female sooty mangabeys use the bigram
twitter_grunt mostly in infant-directed affiliation and the reverse, grunt_twitter, mostly while
feeding. They call this "order-sensitive compositionality" in a monkey. This repository is an
open, pre-registered test of that claim on the authors' public data. Using an exact conditional
permutation, it asks whether the *same* female shifts context with order, or whether the contrast
comes from *which* females use which order.

- `MANGABEY-PREREG.md`: the pre-registration (tests, verdict rules, predictions), written before
  the data file was opened
- `mangabey_test.py`: the analysis (Python standard library only); `test_mangabey_test.py`: unit
  tests with hand-worked expected values
- `gate.py`: the job's first step, which refuses to compute until the registration is public

Data: Le Floch et al., figshare [10.6084/m9.figshare.29503334](https://doi.org/10.6084/m9.figshare.29503334)
v2 (CC BY 4.0). The job downloads the data and does not redistribute it.

MV2, Munim, Inc. (mv2@munimtech.com). Made with AI agents working in MV2's name; no human expert
has checked it yet. Code Apache-2.0; text CC BY 4.0.
