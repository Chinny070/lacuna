# Contract integration

LACUNA has 40 public methods: 17 writes and 23 views. Its constructor takes no
parameters. Run `genvm-lint schema contracts/lacuna.py` for the ABI source.

Safe write sequence:

1. Create a constitution and policy.
2. Create an agreement referencing their active IDs.
3. Submit/freeze baseline evidence; evaluate and resolve challenges.
4. Dual-accept the proposed baseline.
5. Start observation; submit/freeze outcome evidence and explanations.
6. Evaluate performance; resolve an appeal if opened; inspect preview.
7. Both parties call `finalize_verdict`; the second call makes the verdict FINAL.

Only client and contractor addresses may submit evidence, freeze a package,
request evaluation, challenge/appeal, accept a baseline, or finalize. Freezing
fetches each stored evidence URL once under consensus, so a freeze reverts if a
source is unreachable; the first `finalize_verdict` call returns
`AWAITING_COUNTERPARTY_FINALIZATION` rather than finalizing, and resolving an
appeal clears both acknowledgements. Views return JSON strings.
Wait for finalized successful execution before reading derived state. The
Stage 12 React/TypeScript frontend in `frontend/` provides schema-backed
StudioNet adapters for all 40 methods at
`0x0FA601A457a03967a5Ed008e2f82e7966392516A`; it has no backend or transfer
endpoint.
