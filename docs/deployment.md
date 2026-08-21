# StudioNet deployment runbook

Deployment is manual and requires a browser wallet, so it is performed by a
human operator in GenLayer Studio. This document is the procedure.

## What to deploy

- File: `contracts/lacuna.py` -- the entire contract, deployed as a single
  source file. There is no build step, no constructor arguments, and no
  post-deployment initialization call.
- Keep the pinned runner header on line 1 exactly as committed:
  `# { "Depends": "py-genlayer:1jb45aa8ynh2a9c9xn3b7qqh8sm5q93hwfp7jqmwsfhh8jpz09h6" }`
  `genvm-lint` reports that a newer runner exists (I200). Do not take it as
  part of this deployment; changing the runner is a separate, separately
  verified change.
- Record the normalized source digest at deploy time, from the exact working
  tree being deployed:

```bash
python -c "import hashlib,pathlib;print(hashlib.sha256(pathlib.Path('contracts/lacuna.py').read_bytes().replace(b'\r\n',b'\n')).hexdigest())"
```

  For the v0.2.0 protocol-hardening source this is
  `d6aa8bd41ae57784c391e51c720a2516f5bcd246b37d93771e0a10f1c4640656`.

## Current deployment

- Address: `0x964a6e11922F9745d46c906c357dfEDAacC64F91`
- Source: v0.2.1, normalized digest
  `1331446574fae97336f8867ba3ee172566e431ea1ac85d0ef8b714b7787bb2f7`
- Deployed and verified 2026-08-21. On a fresh read, `list_agreements`,
  `list_constitutions`, and `list_settlement_policies` each returned `[]`, and
  an unknown agreement-scoped read reverted through `gen_call` as expected. The
  schema retrieved from the live contract through genlayer-js@1.1.8 matches the
  repository contract: 40 methods, 17 writes, 23 views, zero constructor
  parameters.

Superseded, and not maintained:

- `0x5abdf6380Faaa1f0Eb51cc666A8660D5a8Dd73a6` -- v0.2.0, digest
  `d6aa8bd41ae57784c391e51c720a2516f5bcd246b37d93771e0a10f1c4640656`. Carried
  every protocol guarantee, but its equivalence principles demanded exact
  numeric agreement and could not reach consensus on live validators; see
  `docs/smoke-test.md`.
- `0x0FA601A457a03967a5Ed008e2f82e7966392516A` -- Stage 9, digest
  `d802562731d2744978008585f0a17ef8054b156c55a096c968b297b27a5b0ae2`, before
  the hardening.

GenLayer contracts are not upgraded in place, so each protocol change means a
new address and a full pass of the rewiring checklist below.

The public method surface is unchanged -- 40 methods, 17 writes, 23 views, zero
constructor parameters -- so the recorded `methods` arrays stay valid and no
frontend adapter signature changes. Only the address and deployment metadata
move.

## Preflight

Run from a clean Python 3.12+ environment (`pip install -r requirements-dev.txt`):

1. `genvm-lint check contracts/lacuna.py --json` -- expect `"ok": true` and
   `methods: 40`, `write_methods: 17`, `view_methods: 23`, `ctor_params: 0`.
   The I200 newer-runner notice is expected and is not a failure.
2. `python -m pytest tests/direct/ -v` -- expect 203 passed.
3. `npm --prefix frontend run typecheck && npm --prefix frontend run lint`.
4. Confirm the working tree is clean and you are deploying committed source.

All four passed on the v0.2.0 source at the time this runbook was written.

## Deploy

1. Open GenLayer Studio with an injected StudioNet-compatible wallet.
2. Select StudioNet: chain ID `61999`, RPC `https://studio.genlayer.com/api`.
3. Paste the full contents of `contracts/lacuna.py` and deploy with no
   constructor arguments.
4. Wait for finalized successful execution -- a transaction hash alone is not
   success.
5. Record the new contract address.

## Post-deployment read checks

Against the new address, before wiring anything to it:

- `list_agreements()`, `list_constitutions()`, and `list_settlement_policies()`
  each return `[]` on a fresh deployment.
- `get_constitution_versions("does-not-exist")` and
  `get_settlement_policy_versions("does-not-exist")` return `[]`.
- `get_agreement("does-not-exist")` and `list_verdicts("does-not-exist")`
  revert through the `gen_call` path -- expected for agreement-scoped records
  that do not exist.
- All 23 view methods appear in Studio's ABI and the constructor takes no
  arguments.
- Retrieve the schema through official GenLayerJS and confirm the `methods`
  array matches `docs/deployed-schema.json`.

Then run the live read verifier against the new address:

```bash
VITE_LACUNA_CONTRACT_ADDRESS=<new-address> npm --prefix frontend run verify:live
```

On PowerShell, set the variable first:

```bash
$env:VITE_LACUNA_CONTRACT_ADDRESS = "<new-address>"; npm --prefix frontend run verify:live
```

## Wiring the new address

The address appears in ten tracked places plus two untracked ones. Update all
of them together, or the frontend will read one contract while the docs
describe another:

- `frontend/.env.example` -- `VITE_LACUNA_CONTRACT_ADDRESS`
- `frontend/.env.local` (untracked) -- local development
- Vercel project environment variables (untracked) -- production frontend
- `frontend/src/lib/genlayer/config.ts` -- hardcoded fallback
- `frontend/scripts/verify-live.mjs` -- hardcoded fallback
- `frontend/src/pages.tsx` -- address shown on the integration page
- `frontend/src/lib/genlayer/deployed-schema.json` -- `address`
- `frontend/README.md`
- `docs/deployed-schema.json` -- `address`, `retrieved_at`, and
  `deployed_source_normalized_sha256`
- `docs/integration.md`, `README.md`, and this file

Redeploy the Vercel frontend after changing its environment variables;
build-time `VITE_` values do not update on their own.

## Smoke test

`docs/smoke-test.md` is the post-deployment smoke test: a read pass covering
all 23 view methods (already run against this deployment) and a wallet-driven
write pass that exercises party-gated freezes, snapshot capture under real
consensus, exact-match adjudication, and dual-acknowledged finalization.

## First safe write flow

Create a constitution, policy, and agreement with valid non-zero addresses and
non-overlapping windows. Read every returned ID with its getter. Then submit
baseline evidence from a party address.

Use real lawful evidence URLs; test mocks are not deployment inputs. Freezing
fetches every submitted URL once under consensus, so a source that is
unreachable, or that renders differently for each validator, makes the freeze
revert and leaves the package open -- prefer stable, static evidence pages.

Finalization needs both parties to call `finalize_verdict`, or one party after
the seven-day appeal window closes with no appeal open. A first call returning
`AWAITING_COUNTERPARTY_FINALIZATION` is the expected result, not an error.

Settlement remains advisory: the contract transfers no tokens.
