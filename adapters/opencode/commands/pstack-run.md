---
description: Zero-token task router and execution loop (/pstack-run)
---

Execute Pstack v3.0 zero-token routing and execution for `$ARGUMENTS`:
1. Run `pstack route "$ARGUMENTS"` to classify intent, select role and model tier, and generate `.agents/handoffs/active-brief.md` with AST pointers.
2. Execute the Builder loop via Tab 1 `/pstack-build` or `pstack run "$ARGUMENTS"`.
3. Pass all 4 deterministic verification gates via `pstack verify all`.
4. Trigger independent verifier via `/pstack-verify --blind` and export final deliverables.
