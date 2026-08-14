# Manual StudioNet deployment preparation

LACUNA is deployed on GenLayer StudioNet at
`0x0FA601A457a03967a5Ed008e2f82e7966392516A`.

Do not redeploy this contract from this repository. This document records the
manual Studio deployment and safe post-deployment procedure.

## Preflight

1. Run `genvm-lint check contracts/lacuna.py --json`.
2. Run `python -m pytest tests/direct/ -v`.
3. Confirm zero constructor parameters, 40 methods, 17 writes, and 23 views.
4. Retain the pinned `py-genlayer` dependency header in `contracts/lacuna.py`.
5. Select StudioNet in Studio/wallet and use the canonical address above.
   `docs/deployed-schema.json` records the schema retrieved from the live
   contract through official GenLayerJS.

## Post-deployment read checklist

- `list_agreements()`, `list_constitutions()`, and
  `list_settlement_policies()` returned `[]` during the 2026-08-14 safe-read
  verification.
- `get_constitution_versions("does-not-exist")` and
  `get_settlement_policy_versions("does-not-exist")` returned `[]`.
- `get_agreement("does-not-exist")` and
  `list_verdicts("does-not-exist")` reverted through StudioNet's `gen_call`
  path, as expected for agreement-scoped records that do not exist.
- All 23 view methods appear in Studio's ABI.
- The constructor requires no arguments.

## First safe write flow

Create a constitution, policy, and agreement with valid non-zero addresses and
non-overlapping windows. Read every returned ID using its getter. Then submit
baseline evidence. Use real lawful evidence URLs and hashes; test mocks are
not deployment inputs. Stage 8 settlement is advisory and transfers no tokens.
