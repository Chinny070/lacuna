# Live smoke test

Exercises the deployed contract at
`0x5abdf6380Faaa1f0Eb51cc666A8660D5a8Dd73a6` on StudioNet. The direct test
suite already covers contract logic with mocks; this document covers only what
mocks cannot: real validator consensus, real web fetches, and real wallets.

## Part 1 -- reads (no wallet needed)

Run against the deployed address:

```bash
npm --prefix frontend run verify:live
```

All 23 view methods were exercised on 2026-08-21. Result: `list_agreements`,
`list_constitutions`, `list_settlement_policies`, `get_constitution_versions`,
and `get_settlement_policy_versions` returned `[]`; every agreement-scoped
getter and list reverted for an unknown ID, as expected on an empty contract.

One deliberate deviation: `list_baseline_challenges` returns `[]` for an
unknown baseline instead of reverting, because it reads through
`baseline_challenge_ids.get(baseline_id, "[]")` rather than validating the
baseline first. This is pre-existing Stage 9 behavior, unchanged by v0.2.0, and
inconsistent with the agreement-scoped list views. Harmless, but worth
aligning the next time the contract is redeployed for another reason.

## Part 2 -- writes (wallet required)

Needs three funded StudioNet wallets: CLIENT, CONTRACTOR, and OUTSIDER (used
once, to prove a negative). Every write must reach finalized successful
execution before the next step; a transaction hash is not success, and neither
is a FINALIZED badge next to a Consensus Result of Undetermined.

### Evidence sources

Freeze fetches every submitted URL once under strict-equality consensus, so
evidence pages must be byte-identical for every validator. The fixtures in
`docs/smoke-evidence/` (served from GitHub at a pinned commit) and
`frontend/public/smoke-evidence/` (served from the deployed site) are built for
this: two distinct hosts, immutable content.

They are also written to be numerically unambiguous. The first smoke run used a
short three-month snapshot, and validators split on whether it supported a
baseline at all -- one leader returned VOID, another returned a valid range
from the same frozen bytes. The current fixtures give nine flat months with a
30 bps spread and a peer benchmark, so the counterfactual is roughly 3400 bps
by inspection rather than by extrapolation.

### Windows

Baseline 2025-07-01 to 2026-04-01 (`1751328000` to `1775001600`), observation
2026-04-01 to 2026-07-01 (`1775001600` to `1782864000`). The baseline window is
wide enough to hold the whole historical series as evidence periods; the first
run's three-month window was not.

### Sequence

1. `create_baseline_constitution` -- `"Community Health v1"`,
   `"monthly_churn_bps"`, `["disputes","escalations"]`,
   `["contributor_retention","member_activity"]`,
   `"historical_trend_with_benchmark"`,
   `["PUBLIC_ANALYTICS","COMMUNITY_ACTIVITY"]`, `2`,
   `"Exclude windows overlapping a declared market-wide shock."`,
   `["Prefer explicit later evidence over earlier drafts."]`,
   `["PRE_TREND_CHECK","GUARDRAIL_CHECK"]`

2. `create_settlement_policy` -- `"Standard Settlement v1"`, `2000`, `6000`,
   `8000`, `1500`, `3000`, `4000`

3. `create_agreement` -- CLIENT and CONTRACTOR must be two addresses you can
   both sign from, with the windows above and escrow `10000`.

4. `submit_baseline_evidence` (CLIENT) for each baseline fixture: the two churn
   series and the peer benchmark from GitHub, and the activity baseline from
   the site. Metric refs `monthly_churn_bps` and `member_activity`; periods
   inside the baseline window.

5. `freeze_baseline_evidence` -- from OUTSIDER first, which must revert with
   "Only the agreement's client or contractor". Then from CLIENT. Confirm each
   record then carries `frozen_content`, `frozen_content_hash`, and
   `submitted_content_hash`, with `content_hash` equal to the frozen digest.

6. `evaluate_baseline` -- first real consensus run.

7. `accept_baseline` from CLIENT, then from CONTRACTOR. The first call must
   leave the status at `BASELINE_PROPOSED`.

8. `start_observation`.

9. `submit_outcome_evidence` (CLIENT) for all three outcome fixtures: churn
   (`monthly_churn_bps`, observed `2200`), contributor retention
   (`contributor_retention`, observed `9100`), and member activity
   (`member_activity`, observed `4830`). Freeze refuses unless the primary
   metric and every guardrail metric are covered. Optionally submit an
   alternative explanation to exercise that record.

10. `freeze_resolution` -- OUTSIDER first, then CLIENT.

11. `evaluate_performance` -- second real consensus run.

12. `get_settlement_preview` -- pure arithmetic, must agree with the verdict.

13. `finalize_verdict` from CLIENT: must return
    `AWAITING_COUNTERPARTY_FINALIZATION` with a populated
    `appeal_window_ends_at`. Then from CONTRACTOR: `FINALIZED`.

## What the first run found

Run 1 (contract `0x5abdf6380Faaa1f0Eb51cc666A8660D5a8Dd73a6`, 2026-08-21)
cleared the freeze path completely: both URLs were fetched under
strict-equality consensus, and the contract stored 912 and 826 bytes of frozen
content with matching digests, demoting the submitter hashes to
`submitted_content_hash`. That is the evidence-binding guarantee working on
real validators.

`evaluate_baseline` then failed twice with Consensus Result `Undetermined`
after three leader rotations each, writing no state. The cause was the
equivalence principle demanding exact numeric agreement on every field.
Independent validators do not reproduce judgement numbers digit for digit, and
`confidence_bps` in particular is free-floating: nothing downstream consumes
it. The steward asked that tolerated disagreement not change the settlement
band or caps, which is achievable; exact agreement on every digit is not.

The principles are now consequence-aware. Verdict equivalence is judged on
settlement outcome using the agreement's real policy numbers -- same payment
band, same answer on the confounder and guardrail caps, with a tight bound
inside the continuous partial-payment band -- while confidence and quality
scores carry loose bounds because they gate nothing. Baseline evaluation
carries a bounded tolerance because a proposed baseline settles nothing until
both parties accept it.

## What to watch

Steps 6 and 11 are still the informative ones. If they now finalize with a real
consensus result, the consequence-aware principle works against live
validators. If they go Undetermined again, check whether the leaders disagreed
on a decision field rather than a number -- `method_valid` or a settlement band
-- because no tolerance can paper over that, and it means the evidence itself
is genuinely ambiguous.

Two things this run cannot cover:

- The seven-day appeal window. Step 13 proves the dual-acknowledgement path;
  unilateral finalization after the deadline cannot be reached without waiting
  out the window on a real chain, and is covered only by direct tests.
- Wallet signature and network-switch flows in the deployed frontend, which
  remain a manual browser check.
