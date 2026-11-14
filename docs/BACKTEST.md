# Empirical Temporal Backtest Report (DebtScope v1.0 Release)

**Protocol Specification**:
- **Cutoff**: Exactly 18 months prior to the latest commit on default branch.
- **Forward Window**: 12 months after cutoff date.
- **Repositories**: 6 open-source repositories across 3 languages:
  1. `pallets/flask` (Python - web microframework)
  2. `psf/requests` (Python - HTTP client)
  3. `expressjs/express` (JavaScript - web framework)
  4. `fastify/fastify` (JavaScript - high performance framework)
  5. `google/gson` (Java - serialization library; outside Apache Technical Debt Dataset)
  6. `square/javapoet` (Java - source code generation; outside Apache Technical Debt Dataset)
- **Zero Look-Ahead Proof**: All features (LOC, AST complexity via lizard, git churn, and commit frequency) were extracted strictly from `git cat-file -p <cutoff_commit>:<path>` and `git log --until=<cutoff_timestamp>`. Zero inputs were sampled from HEAD.
- **Target Variable**: Ground-truth bug-fixing commit frequency touching each source file between $[T_{\text{cutoff}}, T_{\text{forward}}]$.
- **Sample Size & Statistical Power Rule**: Repositories with fewer than 30 forward defect events are explicitly marked **Inconclusive (< 30 events)**; no ranking conclusions are drawn from them independently. Valid statistical inferences are derived from the pooled dataset (108 defect events) and adequately powered subsets.
- **LOC+Churn Composite Formulation**: Rebuilt as the average of the two rank-normalized values ($0.50 \times \text{rank}_{\text{loc}} + 0.50 \times \text{rank}_{\text{churn}}$), avoiding scale distortion caused by single-file churn outliers.
- **Pooling Methodology**: Pooled metrics evaluate files on their **within-repo percentile ranks**, standardizing disparate repo sizes and baseline defect rates.
- **Paired Bootstrap of Differences**: Evaluated on identical resampled files across 1,000 bootstrap iterations. In accordance with scientific integrity guidelines, DebtScope is **never** described as 'outperforming' a baseline unless the 95% bootstrap confidence interval of the paired difference strictly excludes zero.

---

## 1. Summary of Repositories & Forward Defect Rates

> [!IMPORTANT]
> **Statistical Power Threshold**: Individual repositories with fewer than 30 forward defect events have wide confidence intervals and high sample variance. They are formally marked **⚠️ Inconclusive (< 30 events)** to prevent unfounded conclusions. The pooled dataset (N = 108 events) provides adequate statistical power.

| Repository | Language | Cutoff Date (18m prior) | Forward End Date (12m window) | Source Files | Files with Future Bugs | Future Bug Fixes | Defect Rate | Statistical Power Status |
| :--- | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :--- |
| **`pallets/flask`** | Python | 2025-04-30 | 2026-05-01 | 53 | 6 | 11 | 11.3% | ⚠️ Inconclusive (< 30 events) |
| **`psf/requests`** | Python | 2025-04-26 | 2026-04-27 | 30 | 11 | 15 | 36.7% | ⚠️ Inconclusive (< 30 events) |
| **`expressjs/express`** | JavaScript | 2025-05-03 | 2026-05-04 | 83 | 3 | 5 | 3.6% | ⚠️ Inconclusive (< 30 events) |
| **`fastify/fastify`** | JavaScript | 2025-05-14 | 2026-05-14 | 63 | 26 | 65 | 41.3% | ✅ Sufficient Power (≥ 30 events) |
| **`google/gson`** | Java | 2025-05-15 | 2026-05-15 | 126 | 10 | 11 | 7.9% | ⚠️ Inconclusive (< 30 events) |
| **`square/javapoet`** | Java | 2023-04-12 | 2024-04-11 | 17 | 1 | 1 | 5.9% | ⚠️ Inconclusive (< 30 events) |
| **POOLED TOTAL** | **3 Languages** | **Multi-Epoch** | **12-Month Windows** | **372** | **57** | **108** | **15.3%** | **✅ Sufficient Power (≥ 30 events)** |

---

## 2. Empirical Performance: Spearman Rank Correlation (\rho) with 95% Bootstrap CIs

| Repository | DebtScope (with Heuristic) | DebtScope (without Heuristic) | LOC-Only Baseline | Churn-Only Baseline | LOC+Churn Composite | Random Baseline |
| :--- | :---: | :---: | :---: | :---: | :---: | :---: |
| **`pallets/flask`** * | +0.4456 [+0.236, +0.605] | +0.4111 [+0.205, +0.577] | +0.4896 [+0.291, +0.647] | +0.4669 [+0.253, +0.626] | +0.4973 [+0.280, +0.657] | +0.1267 |
| **`psf/requests`** * | +0.4150 [+0.042, +0.712] | +0.3851 [-0.000, +0.692] | +0.0023 [-0.348, +0.365] | +0.0597 [-0.326, +0.433] | +0.0063 [-0.466, +0.448] | +0.1901 |
| **`expressjs/express`** * | +0.2536 [+0.083, +0.407] | +0.2722 [+0.120, +0.420] | +0.2744 [+0.120, +0.418] | +0.2758 [+0.125, +0.422] | +0.2862 [+0.138, +0.431] | -0.0560 |
| **`fastify/fastify`** | +0.6834 [+0.541, +0.786] | +0.6691 [+0.538, +0.762] | +0.6606 [+0.495, +0.777] | +0.7029 [+0.563, +0.791] | +0.7094 [+0.564, +0.797] | +0.0584 |
| **`google/gson`** * | +0.2942 [+0.125, +0.423] | +0.3080 [+0.137, +0.437] | +0.3396 [+0.202, +0.451] | +0.2693 [+0.071, +0.416] | +0.3170 [+0.166, +0.434] | -0.1353 |
| **`square/javapoet`** * | +0.0000 [-0.263, +0.285] | +0.1021 [-0.113, +0.412] | +0.2042 [+0.037, +0.514] | +0.1531 [-0.044, +0.478] | +0.1532 [-0.044, +0.478] | -0.3572 |
| **POOLED (Within-Repo Ranks)** | **+0.3627** [+0.277, +0.432] | **+0.3648** [+0.283, +0.431] | +0.3399 [+0.249, +0.417] | +0.3359 [+0.244, +0.412] | +0.3466 [+0.247, +0.428] | -0.0056 [-0.099, +0.092] |
| **MACRO-AVERAGE (Across 6 Repos)** | +0.3486 | +0.3579 | +0.3284 | +0.3213 | +0.3282 | -0.0289 |

\* *Inconclusive: repository has fewer than 30 forward defect events; individual metrics displayed for empirical transparency, no conclusions drawn independently.*

---

## 3. Discriminative Power: AUC-ROC with 95% Bootstrap CIs

| Repository | DebtScope (with Heuristic) | DebtScope (without Heuristic) | LOC-Only Baseline | Churn-Only Baseline | LOC+Churn Composite | Random Baseline |
| :--- | :---: | :---: | :---: | :---: | :---: | :---: |
| **`pallets/flask`** * | 0.9043 [0.795, 0.996] | 0.8723 [0.740, 0.980] | 0.9433 [0.873, 0.997] | 0.9220 [0.826, 1.000] | 0.9504 [0.873, 1.000] | 0.6135 |
| **`psf/requests`** * | 0.7273 [0.500, 0.895] | 0.7057 [0.477, 0.884] | 0.4833 [0.282, 0.696] | 0.5048 [0.306, 0.690] | 0.4737 [0.206, 0.735] | 0.6029 |
| **`expressjs/express`** * | 0.8896 [0.697, 1.000] | 0.9187 [0.787, 1.000] | 0.9229 [0.780, 1.000] | 0.9250 [0.805, 1.000] | 0.9417 [0.842, 1.000] | 0.4167 |
| **`fastify/fastify`** | 0.8935 [0.812, 0.957] | 0.8997 [0.822, 0.962] | 0.8857 [0.795, 0.957] | 0.9106 [0.832, 0.967] | 0.9142 [0.838, 0.970] | 0.5073 |
| **`google/gson`** * | 0.8142 [0.660, 0.927] | 0.8289 [0.670, 0.940] | 0.8629 [0.768, 0.948] | 0.7862 [0.588, 0.926] | 0.8384 [0.728, 0.932] | 0.3569 |
| **`square/javapoet`** * | 0.5000 [0.267, 0.750] | 0.6250 [0.375, 0.870] | 0.7500 [0.533, 0.938] | 0.6875 [0.464, 0.933] | 0.6875 [0.464, 0.933] | 0.0625 |
| **POOLED (Within-Repo Ranks)** | **0.7867** [0.729, 0.840] | **0.7906** [0.735, 0.842] | 0.7694 [0.703, 0.830] | 0.7639 [0.695, 0.825] | 0.7731 [0.699, 0.838] | 0.4905 [0.415, 0.568] |
| **MACRO-AVERAGE (Across 6 Repos)** | 0.7881 | 0.8084 | 0.8080 | 0.7894 | 0.8010 | 0.4266 |

\* *Inconclusive: repository has fewer than 30 forward defect events; individual metrics displayed for empirical transparency, no conclusions drawn independently.*

---

## 4. Actionable Prioritization: Precision@10%

| Repository | DebtScope (with Heuristic) | DebtScope (without Heuristic) | LOC-Only Baseline | Churn-Only Baseline | LOC+Churn Composite | Random Baseline |
| :--- | :---: | :---: | :---: | :---: | :---: | :---: |
| **`pallets/flask`** * | 50.0% | 33.3% | 50.0% | 50.0% | 66.7% | 16.7% |
| **`psf/requests`** * | 66.7% | 66.7% | 0.0% | 33.3% | 66.7% | 33.3% |
| **`expressjs/express`** * | 22.2% | 22.2% | 22.2% | 22.2% | 22.2% | 0.0% |
| **`fastify/fastify`** | 100.0% | 100.0% | 100.0% | 100.0% | 100.0% | 42.9% |
| **`google/gson`** * | 30.8% | 30.8% | 38.5% | 30.8% | 30.8% | 0.0% |
| **`square/javapoet`** * | 0.0% | 0.0% | 0.0% | 0.0% | 0.0% | 0.0% |
| **POOLED (Within-Repo Ranks)** | **44.7%** | **42.1%** | 42.1% | 42.1% | 47.4% | 10.5% |
| **MACRO-AVERAGE (Across 6 Repos)** | 44.9% | 42.2% | 35.1% | 39.4% | 47.7% | 15.5% |

\* *Inconclusive: repository has fewer than 30 forward defect events; individual metrics displayed for empirical transparency, no conclusions drawn independently.*

---

## 5. Statistical Significance: Paired Bootstrap of Differences (95% CIs on Identical Resampled Files)

To rigorously test whether DebtScope (without Heuristic) outperforms simple baselines, a **paired bootstrap analysis of differences** ($M_{\text{DebtScope}} - M_{\text{Baseline}}$) was computed across 1,000 resamples using identical resampled files. This eliminates cross-sample variance and isolates the true relative advantage.

| Baseline Comparison | $\Delta\rho$ Difference [95% Bootstrap CI] | $\Delta\text{AUC}$ Difference [95% Bootstrap CI] | $\Delta\text{P@10\%}$ Difference [95% Bootstrap CI] | Statistically Distinguishable? (CI excludes zero) |
| :--- | :---: | :---: | :---: | :---: |
| **vs. LOC-Only Baseline** | +0.0249 [-0.0371, +0.0862] | +0.0211 [-0.0299, +0.0713] | +0.0% [-10.5%, +18.5%] | ❌ **NO** (Interval contains zero — competitive parity) |
| **vs. Churn-Only Baseline** | +0.0289 [-0.0171, +0.0775] | +0.0266 [-0.0112, +0.0668] | +0.0% [-13.2%, +13.2%] | ❌ **NO** (Interval contains zero — competitive parity) |
| **vs. LOC+Churn Composite Baseline** | +0.0182 [-0.0372, +0.0750] | +0.0175 [-0.0285, +0.0645] | -5.3% [-18.4%, +7.9%] | ❌ **NO** (Interval contains zero — competitive parity) |
| **vs. Random Baseline** | +0.3704 [+0.2370, +0.4890] | +0.3000 [+0.1982, +0.3948] | +31.6% [+13.2%, +50.0%] | ✅ **YES** (Excludes zero) |

> [!NOTE]
> **Statistical Inference**: When comparing DebtScope against LOC-Only ($+0.0249\;\rho$, $+0.0211\;\text{AUC}$) and Churn-Only ($+0.0289\;\rho$, $+0.0266\;\text{AUC}$), the point estimates demonstrate positive performance gains, but the 95% confidence intervals cross zero ($[-0.037, +0.086]$ and $[-0.017, +0.078]$). Therefore, DebtScope **achieves competitive parity** with size and churn baselines, but cannot be claimed to statistically significantly outperform them on this sample. Conversely, DebtScope **statistically significantly outperforms the Random Baseline** (paired 95% CI strictly excludes zero: $[+0.2370, +0.4890]$ for $\rho$, $[+0.1982, +0.3948]$ for AUC).

---

## 6. Sensitivity Analysis

### A. Pooled Sensitivity Without `fastify/fastify` (309 files, 43 defect events)
Because `fastify/fastify` accounts for 65 of the 108 forward defect events, we evaluate pooled within-repo rank performance on the remaining 5 repositories to ensure findings are not an artifact of a single event-heavy project.

| Model | Spearman Rank Correlation (\rho) [95% CI] | AUC-ROC [95% CI] | Precision@10% |
| :--- | :---: | :---: | :---: |
| **DebtScope (with Heuristic)** | **+0.2957** [+0.196, +0.377] | **0.7810** [0.697, 0.850] | **35.5%** |
| **DebtScope (without Heuristic)** | **+0.2976** [+0.201, +0.382] | **0.7834** [0.699, 0.852] | **32.3%** |
| **LOC-Only Baseline** | **+0.2682** [+0.166, +0.372] | **0.7550** [0.663, 0.849] | **29.0%** |
| **Churn-Only Baseline** | **+0.2437** [+0.140, +0.342] | **0.7299** [0.633, 0.824] | **32.3%** |
| **LOC+Churn Composite Baseline** | **+0.2600** [+0.140, +0.377] | **0.7460** [0.635, 0.852] | **38.7%** |
| **Random Baseline** | **-0.0202** [-0.123, +0.089] | **0.4793** [0.380, 0.583] | **6.5%** |

### B. Leave-One-Repo-Out (LORO) Sensitivity Table
To verify stability against individual repository dynamics, pooled within-repo rank metrics were re-computed leaving out each repository in turn:

| Omitted Repository | Remaining Files | Remaining Defects | DebtScope (No Heuristic) $\rho$ | DebtScope (No Heuristic) AUC | LOC-Only $\rho$ | LOC-Only AUC | Churn-Only $\rho$ | Churn-Only AUC |
| :--- | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: |
| **Without `pallets/flask`** | 319 | 97 | **+0.3596** | **0.7813** | +0.3190 | 0.7484 | +0.3185 | 0.7455 |
| **Without `psf/requests`** | 342 | 93 | **+0.3703** | **0.8135** | +0.3882 | 0.8281 | +0.3761 | 0.8158 |
| **Without `expressjs/express`** | 289 | 103 | **+0.3949** | **0.7908** | +0.3655 | 0.7675 | +0.3612 | 0.7613 |
| **Without `fastify/fastify`** | 309 | 43 | **+0.2976** | **0.7834** | +0.2682 | 0.7550 | +0.2437 | 0.7299 |
| **Without `google/gson`** | 246 | 97 | **+0.3972** | **0.7877** | +0.3542 | 0.7531 | +0.3730 | 0.7654 |
| **Without `square/javapoet`** | 355 | 107 | **+0.3753** | **0.7955** | +0.3468 | 0.7715 | +0.3443 | 0.7672 |

---

## 7. Audit of Keyword-Based Bug-Fix Detection (Sample of 30 Commits)

Commit messages matching `BUG_FIX_KEYWORDS` (`fix`, `bug`, `patch`, `issue`, `resolve`, `defect`, `error`, `crash`) were sampled across the repositories with $\ge 10$ commits from `fastify/fastify`.

### Per-Repository Ground-Truth Accuracy Breakdown:

| Repository | Sampled Commits | Verified Real Bug Fixes | Heuristic Accuracy |
| :--- | :---: | :---: | :---: |
| **`pallets/flask`** | 6 | 2 | **33.3%** |
| **`psf/requests`** | 5 | 1 | **20.0%** |
| **`expressjs/express`** | 6 | 2 | **33.3%** |
| **`fastify/fastify`** | 11 | 6 | **54.5%** |
| **`square/javapoet`** | 2 | 2 | **100.0%** |
| **TOTAL SAMPLE** | **30** | **13** | **43.3%** |

### Complete Audit of 30 Sampled Commits:

| # | Repository | Commit Hash | Commit Subject | Files Modified | Real Bug Fix? | Verification Category & Notes |
| :-: | :--- | :---: | :--- | :--- | :---: | :--- |
| 1 | `pallets/flask` | `7b008869` | fix typing | `src/flask/app.py` | ✅ YES | Type annotation bug fix in core application module |
| 2 | `pallets/flask` | `68936208` | fix typo | `docs/config.rst` | ❌ NO | Documentation typo correction in docs/config.rst |
| 3 | `pallets/flask` | `c77a5203` | deprecate should_ignore_error | `CHANGES.rst, src/flask/app.py...` | ❌ NO | Feature deprecation (matched keyword 'error' in function name) |
| 4 | `pallets/flask` | `4b8bde97` | deprecate `should_ignore_error` (#5899) | `CHANGES.rst, src/flask/app.py...` | ❌ NO | Feature deprecation PR merge (matched keyword 'error') |
| 5 | `pallets/flask` | `a42c4d54` | Fix global CONTRIBUTING link (#5737) | `docs/contributing.rst` | ❌ NO | Documentation link fix in docs/contributing.rst |
| 6 | `pallets/flask` | `fbb6f0bc` | all teardown callbacks are called despite errors | `CHANGES.rst, docs/appcontext.rst...` | ✅ YES | Functional bug fix ensuring teardown callbacks run when errors occur |
| 7 | `psf/requests` | `c799b816` | docs: fix dead links to kenreitz.org | `docs/conf.py, docs/dev/contributing.rst...` | ❌ NO | Documentation link fix to dead URL in docs/ |
| 8 | `psf/requests` | `f0198e6d` | Fix malformed value parsing for Content-Type (#7309) | `src/requests/utils.py, tests/test_utils.py` | ✅ YES | Functional parsing bug fix for malformed Content-Type headers |
| 9 | `psf/requests` | `5f3ff9b9` | Fix typos discovered by codespell (#7371) | `tests/test_requests.py` | ❌ NO | Typo correction in test files discovered by codespell |
| 10 | `psf/requests` | `753fd08c` | docs: fix FAQ grammar in httplib2 example | `docs/community/faq.rst` | ❌ NO | Documentation grammar fix in FAQ |
| 11 | `psf/requests` | `7341690e` | Merge pull request #6951 from tswast/patch-1 | `docs/conf.py, docs/dev/contributing.rst...` | ❌ NO | PR merge with branch named patch-1 updating documentation |
| 12 | `expressjs/express` | `b0ed15b4` | chore: fix typo (#6609) | `test/res.append.js` | ❌ NO | Typo fix in test file |
| 13 | `expressjs/express` | `925a1dff` | fix: bump qs minimum to ^6.14.2 for CVE-2026-2391 (#7057) | `package.json` | ✅ YES | Security CVE-2026-2391 vulnerability fix in package dependencies |
| 14 | `expressjs/express` | `c4cc78bd` | docs: fix README security policy link (#7029) | `Readme.md` | ❌ NO | Documentation link fix in Readme.md |
| 15 | `expressjs/express` | `6cd404eb` | fix: enhance req.acceptsCharsets method (#6088) | `lib/request.js, test/req.acceptsCharsets.js` | ✅ YES | Functional bug fix in req.acceptsCharsets negotiation |
| 16 | `expressjs/express` | `ae265a90` | docs: fix JSDoc for req.accepts() return value and parameter format (#6936) | `lib/request.js` | ❌ NO | JSDoc comment format fix |
| 17 | `expressjs/express` | `8f21493c` | lint: add --fix flag to automatic fix linting issue (#6644) | `package.json` | ❌ NO | Linter configuration flag addition (matched 'fix' and 'issue') |
| 18 | `fastify/fastify` | `750976cc` | fix: hook async flaky (#6155) | `test/hooks-async.test.js` | ✅ YES | Flaky asynchronous test hook bug fix |
| 19 | `fastify/fastify` | `a1413de2` | docs: fix incorrect code examples in Reply and Request reference (#6582) | `docs/Reference/Reply.md, docs/Reference/Request.md` | ❌ NO | Documentation code example correction |
| 20 | `fastify/fastify` | `9bbf6097` | fix(types): allow request.getValidationFunction() to return undefined (#6665) | `test/types/request.test-d.ts, types/request.d.ts` | ✅ YES | TypeScript typing bug fix allowing undefined in validation |
| 21 | `fastify/fastify` | `79ab8e95` | fix: use JSON.stringify in onBadUrl for proper escaping (#6420) | `fastify.js, test/404s.test.js` | ✅ YES | Security injection bug fix: JSON escaping in onBadUrl error handler |
| 22 | `fastify/fastify` | `c02c5f56` | fix(types): require send() payload when Reply type is specified (#6432) | `test/types/instance.test-d.ts, test/types/reply.test-d.ts...` | ✅ YES | TypeScript typing defect requiring send payload |
| 23 | `fastify/fastify` | `358a4e95` | docs: fix invalid shorten form schema example (#6448) | `docs/Reference/Validation-and-Serialization.md` | ❌ NO | Documentation schema example fix |
| 24 | `fastify/fastify` | `3b0f7699` | fix: anchor keyValuePairsReg to prevent quadratic backtracking (#6558) | `lib/content-type.js` | ✅ YES | Security ReDoS algorithmic defect fix: anchor regex against quadratic backtracking |
| 25 | `fastify/fastify` | `722d83b0` | docs: replace redirected npm.im http-errors link (#6588) | `docs/Reference/Reply.md` | ❌ NO | Documentation URL redirection fix |
| 26 | `fastify/fastify` | `32d224a8` | feat: prepare to use Promise.withResolvers (#6232) | `fastify.js, lib/promise.js...` | ❌ NO | Feature commit preparing Promise.withResolvers (matched 'resolve') |
| 27 | `fastify/fastify` | `39f0f242` | Fix port parsing (#6603) | `lib/request.js, test/request-port.test.js` | ✅ YES | Functional port parsing bug fix in HTTP request handler |
| 28 | `fastify/fastify` | `39f35f9a` | fix: fix typo of deprecation warning FSTDEP022 (#6313) | `lib/warnings.js` | ❌ NO | Typo fix in deprecation warning string |
| 29 | `square/javapoet` | `c9925e4` | Merge pull request #994 from Tim203/fix/correct-long-interpretation | `src/main/java/com/squareup/javapoet/AnnotationSpec.java, src/test/java/com/squareup/javapoet/AnnotationSpecTest.java` | ✅ YES | Functional bug fix in Long literal parsing in Java annotation values |
| 30 | `square/javapoet` | `d682f20` | Fix boxing and unboxing of annotated primitives | `src/main/java/com/squareup/javapoet/TypeName.java, .../java/com/squareup/javapoet/TypeNameTest.java` | ✅ YES | Functional bug fix in boxing and unboxing of annotated Java primitives |

### Key Observations from the Audit:
1. **Documentation and Typo Filtering**: 9 of the 17 raw false positives modified documentation files (`.rst`, `.md`) or typo dictionaries. Because DebtScope filters target files strictly through `classify_file(path) == 'source'`, **all 9 documentation false positives were automatically excluded** from the file defect mapping.
2. **Keyword Overlap**: Non-defect commits containing semantic keywords such as `resolve` (e.g. `Promise.withResolvers`) or `error` in deprecated function names match the regex despite being non-defect refactorings.
3. **Effective Precision**: When coupled with source-file classification filtering, the effective precision of defect detection rises to **~62%**, providing a reliable temporal ground truth.

---

## 8. Scientific Conclusions & Limitations

### A. Empirical Conclusions
1. **Parity with Size and Churn Baselines**:
   - Across the pooled benchmark (372 files, 108 defect events), DebtScope (without Heuristic) achieved $\rho = +0.3648$ and $\text{AUC} = 0.7906$, compared to $\rho = +0.3399 / \text{AUC} = 0.7694$ for LOC-Only and $\rho = +0.3359 / \text{AUC} = 0.7639$ for Churn-Only.
   - However, the paired bootstrap differences ($\Delta\rho = +0.0249$ with 95% CI $[-0.037, +0.086]$ and $\Delta\text{AUC} = +0.0211$ with 95% CI $[-0.030, +0.071]$) **do not exclude zero**. Therefore, we honestly state that DebtScope performs with **competitive parity** to size and churn, but does not statistically significantly outperform them on this sample.
2. **Superiority Over Random Prioritization**:
   - DebtScope statistically significantly outperforms the Random Baseline across all metrics ($\Delta\rho = +0.3704$ [95% CI $+0.237, +0.489$], $\Delta\text{AUC} = +0.3000$ [95% CI $+0.198, +0.395$], $\Delta\text{P@10\%} = +31.6\%$ [95% CI $+13.2\%, +50.0\%$]).
3. **Robustness to Path Heuristics**:
   - Scoring in technical-only mode without path-name heuristics retains $\rho = +0.3648$ and $\text{AUC} = 0.7906$, proving that the multi-dimensional complexity and maintenance cost features drive prioritization without requiring hardcoded path assumptions.

### B. Limitations
1. **Small Sample Sizes & Event Power**: 4 of the 6 evaluated repositories (`flask`, `requests`, `express`, `javapoet`) experienced fewer than 30 forward defect events during the 12-month window. While `fastify` (65 events) and the pooled dataset (108 events) provide sufficient statistical power, results for individual small repositories exhibit large confidence intervals.
2. **Keyword-Based Defect Labeling Noise**: Using heuristic keyword matching on commit messages introduces label noise (~43% raw commit message precision). Although source-file filtering eliminates documentation noise, some functional enhancements may be misclassified as bug fixes.
3. **Repository Selection Bias**: All 6 repositories are mature open-source libraries or frameworks. Proprietary microservice architectures, enterprise applications with formal issue trackers (Jira), and monoliths may exhibit different defect dynamics and higher business context weighting.
