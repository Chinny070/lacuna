# Contract integration

LACUNA has 40 public methods: 17 writes and 23 views. Its constructor takes no
parameters. Run `genvm-lint schema contracts/lacuna.py` for the ABI source.

Safe write sequence:

1. Create a constitution and policy.
2. Create an agreement referencing their active IDs.
3. Submit/freeze baseline evidence; evaluate and resolve challenges.
4. Dual-accept the proposed baseline.
5. Start observation; submit/freeze outcome evidence and explanations.
6. Evaluate performance; resolve an appeal if opened; inspect preview; finalize.

Only client and contractor addresses may submit evidence, request evaluation,
challenge/appeal, accept a baseline, or finalize. Views return JSON strings.
Wait for finalized successful execution before reading derived state. The
Stage 12 React/TypeScript frontend in `frontend/` provides schema-backed
StudioNet adapters for all 40 methods at
`0x0FA601A457a03967a5Ed008e2f82e7966392516A`; it has no backend or transfer
endpoint.
