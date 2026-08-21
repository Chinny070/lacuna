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

Needs three funded StudioNet wallets: CLIENT, CONTRACTOR, and OUTSIDER (the
last is used once, to prove a negative). Every write must reach finalized
successful execution before the next step; a transaction hash is not success.

### Evidence sources

Freeze fetches every submitted URL once under strict-equality consensus, so
evidence pages must be byte-identical for every validator. Publish two small
static files before starting and pin each URL to an immutable revision:

- a `raw.githubusercontent.com` URL pinned to a commit SHA (not a branch name)
- a `gist.githubusercontent.com` URL pinned to a revision SHA

Two different hosts are required -- the constitution below demands two
independent sources. Give each file a few plausible lines of monthly churn and
community-activity figures for the stated periods; the adjudicator judges the
content, so a file with no usable numbers will legitimately produce a VOID
baseline and stop the run at step 6.

Branch names, dashboards, search pages, and anything with a timestamp or
rotating content will make the freeze revert. That is the intended behavior,
not a bug.

### Sequence

1. `create_baseline_constitution` (any wallet)
   `"Community Health v1"`, `"monthly_churn_bps"`,
   `["disputes","escalations"]`, `["contributor_retention","member_activity"]`,
   `"historical_trend_with_benchmark"`,
   `["PUBLIC_ANALYTICS","COMMUNITY_ACTIVITY"]`, `2`,
   `"Exclude windows overlapping a declared market-wide shock."`,
   `["Prefer explicit later evidence over earlier drafts."]`,
   `["PRE_TREND_CHECK","GUARDRAIL_CHECK"]`

2. `create_settlement_policy` (any wallet)
   `"Standard Settlement v1"`, `2000`, `6000`, `8000`, `1500`, `3000`, `4000`

3. `create_agreement` (any wallet) -- use the IDs returned above
   `"SMOKE-1"`, CLIENT, CONTRACTOR, `"Maintain community stability"`,
   `"Keep churn and disputes low for six months."`, constitution_id, policy_id,
   `1767225600`, `1775001600`, `1775001600`, `1782864000`, `10000`

4. `submit_baseline_evidence` (CLIENT), twice:
   - `"SMOKE-EV-1"`, `"SMOKE-1"`, `"PUBLIC_ANALYTICS"`, raw.githubusercontent
     URL, any 64-char lowercase hex string, a one-line summary,
     `"monthly_churn_bps"`, `1767225600`, `1769904000`
   - `"SMOKE-EV-2"`, `"SMOKE-1"`, `"COMMUNITY_ACTIVITY"`, gist URL, a
     different 64-char hex string, a one-line summary, `"member_activity"`,
     `1769904000`, `1772323200`

   `content_hash` is now only a duplicate-submission identifier. Freeze
   replaces it with the digest of what the protocol actually fetched.

5. `freeze_baseline_evidence("SMOKE-1")` from OUTSIDER first -- **must revert**
   with "Only the agreement's client or contractor". Then from CLIENT, which
   must succeed. Read `get_baseline_evidence("SMOKE-EV-1")` afterwards and
   confirm `frozen_content`, `frozen_content_hash`, and
   `submitted_content_hash` are all populated, and that `content_hash` now
   equals `frozen_content_hash`.

6. `evaluate_baseline("SMOKE-1")` (CLIENT or CONTRACTOR). This is the first
   real consensus run. See "What to watch" below.

7. `accept_baseline("SMOKE-1")` from CLIENT, then from CONTRACTOR. The first
   call must leave the status at `BASELINE_PROPOSED`; the second moves it to
   `BASELINE_FINAL`.

8. `start_observation("SMOKE-1")`.

9. `submit_outcome_evidence` (CLIENT) for the primary metric, period
   `1775001600`-`1777593600`, plus at least one guardrail-metric item over
   `1777593600`-`1780272000`, using stable URLs on the same two hosts.
   Optionally `submit_alternative_explanation` to exercise that record.

10. `freeze_resolution("SMOKE-1")` -- again try OUTSIDER first and confirm it
    reverts.

11. `evaluate_performance("SMOKE-1")` -- the second real consensus run.

12. `get_settlement_preview("SMOKE-1")` -- pure arithmetic, should return
    immediately and agree with the verdict's `performance_bps`.

13. `finalize_verdict("SMOKE-1")` from CLIENT. Must return
    `AWAITING_COUNTERPARTY_FINALIZATION` with a populated
    `appeal_window_ends_at`, leaving status at `VERDICT_PROPOSED`. Then call it
    from CONTRACTOR: status becomes `FINALIZED` and the verdict becomes
    `FINAL`.

## What to watch

The single most informative result is whether steps 6 and 11 reach consensus
at all. v0.2.0 requires every decision-bearing number to match exactly across
validators, replacing a +/-1500 bps tolerance. That is the correct guarantee --
base payment scales linearly between the policy thresholds, so any tolerated
spread would move the payout -- but it is strictly harder for independent LLM
validators to satisfy. If these steps revert on equivalence rather than on
validation, that is a real finding about the tolerance level, not a deployment
problem, and it is better learned here than in a live settlement.

Two things this run cannot cover:

- The seven-day appeal window. Step 13 proves the dual-acknowledgement path;
  unilateral finalization after the deadline cannot be reached without waiting
  out the window on a real chain, and is covered only by direct tests.
- Wallet signature and network-switch flows in the deployed frontend, which
  remain a manual browser check.
