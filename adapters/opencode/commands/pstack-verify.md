---
description: Execute Pstack v3.0 Tab 2 Independent Verifier loop (/pstack-verify)
---

Act as the stateless Pstack Independent Verifier in a clean session (`$ARGUMENTS`):
1. Run `pstack verify prep-verifier --blind` and read `.agents/handoffs/blind-review-pack.md` in read-only mode.
2. Audit the Deliverable Contract against actual `git diff --stat`, file pointers, and runtime SHA256 digest.
3. Write your 4-tier adversarial review (`ACT_ON`, `CONSIDER`, `NOTED`, `DISMISSED`) and final `VERDICT: PASS` or `VERDICT: REJECT` to `.agents/handoffs/verifier-verdict.md`.
4. Run `pstack verify verdict` to enforce the verdict gate and automatically export `.agents/handoffs/output-final.md`.
