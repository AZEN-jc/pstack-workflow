---
description: Run Pstack v3.0 reproducible benchmark suite and 12-case adversarial gate test (/pstack-bench)
---

Run Pstack v3.0 reproducible benchmark and unit test verification:
1. Run `pstack test` to execute the standard library unit test suite (`tests/test_pstack_harness.py`).
2. Run `pstack bench` to measure Tier 0/1/2 context compression ratio and verify 12/12 (100%) adversarial mutation interception.
3. Inspect `benchmarks/latest-report.md` and `benchmarks/latest-metrics.json` for empirical metrics.
