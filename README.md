# LACUNA

LACUNA is a GenLayer intelligent contract for settling performance agreements
against a **locked counterfactual baseline**. It addresses the hard question:
what outcome was reasonably expected without the contractor's work, and did the
observed world materially exceed that range?

## Why it exists

Performance settlement is vulnerable to hindsight, cherry-picked metrics,
metric changes, and arguments over product launches, marketing, seasonality,
market movement, or other-team work. LACUNA locks methodology and baseline
evidence before observation, then freezes outcome evidence and competing
explanations before attribution is adjudicated.

GenLayer handles evidence interpretation: counterfactual construction,
challenges, attribution, and appeals. Deterministic contract code controls
authorization, storage, validation, state transitions, and settlement math.

## Lifecycle

`DRAFT → BASELINE_OPEN → BASELINE_FROZEN → BASELINE_PROPOSED →`
`BASELINE_CHALLENGED → BASELINE_PROPOSED | BASELINE_FROZEN → BASELINE_FINAL →`
`OBSERVING → RESOLUTION_OPEN → RESOLUTION_FROZEN → VERDICT_PROPOSED →`
`APPEALED → VERDICT_PROPOSED | RESOLUTION_FROZEN → FINALIZED`

Client and contractor both accept the baseline before `BASELINE_FINAL`. Its
methodology, expected range, frozen baseline evidence, constitution reference,
and settlement-policy reference are then locked for the agreement.

## Attribution and settlement

LACUNA does not ask whether a contractor “did a good job.” It asks whether the
outcome exceeded the locked expected range and how much of that deviation is
credibly attributable after competing explanations, guardrails, evidence
quality, and falsification checks. Alternative explanations are first-class
records; their submitted strengths are claims, not authoritative attribution.

This also applies to negative-space cases: unexpectedly low incidents do not
automatically mean the contractor prevented them. Environmental or security
changes and competing explanations remain in scope.

`get_settlement_preview` is pure integer arithmetic. Base payment is zero
below the minimum threshold, linearly scales to escrow at the full threshold,
and never exceeds escrow. Confounder/guardrail caps are reproducible. Bonus is
advisory only: LACUNA has no bonus pool or production token-transfer logic.

## Architecture and limitations

- Contract: `contracts/lacuna.py`; no backend or admin override.
- Tests: `tests/direct`; all web/LLM calls are mocked in regression tests.
- Only frozen stored evidence URLs are fetched. Content is bounded, delimited,
  and explicitly treated as untrusted evidence, not instructions.
- `source_host` stores the raw normalized hostname. Different subdomains may
  share an owner; LACUNA does not claim this proves independence because safe
  registrable-domain normalization needs public-suffix data.
- Canonical StudioNet deployment:
  `0x0FA601A457a03967a5Ed008e2f82e7966392516A`. The deployed source matches
  the audited Stage 9 source after newline normalization; its schema snapshot
  is recorded in `docs/deployed-schema.json`.
- No production transfer path exists. The React/TypeScript frontend in
  `frontend/` connects directly to the canonical StudioNet deployment and
  treats a write as successful only after finalized successful execution.

See `docs/` for constitutions, policy, evidence, security, integration, and
StudioNet deployment preparation.
