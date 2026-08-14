# Manual StudioNet deployment preparation

Do not deploy automatically from this repository. LACUNA is prepared for
manual GenLayer Studio deployment only.

## Preflight

1. Run `genvm-lint check contracts/lacuna.py --json`.
2. Run `python -m pytest tests/direct/ -v`.
3. Confirm zero constructor parameters, 40 methods, 17 writes, and 23 views.
4. Retain the pinned `py-genlayer` dependency header in `contracts/lacuna.py`.
5. Select StudioNet in Studio/wallet. Do not invent a contract address; record
   the address only after Studio returns the actual deployment result.

## Post-deployment read checklist

- `list_agreements()`, `list_constitutions()`, and
  `list_settlement_policies()` return `[]` on a fresh contract.
- All 23 view methods appear in Studio's ABI.
- The constructor requires no arguments.

## First safe write flow

Create a constitution, policy, and agreement with valid non-zero addresses and
non-overlapping windows. Read every returned ID using its getter. Then submit
baseline evidence. Use real lawful evidence URLs and hashes; test mocks are
not deployment inputs. Stage 8 settlement is advisory and transfers no tokens.
