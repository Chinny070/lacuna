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
and settlement-policy reference are then locked for the agreement. Only an
agreement party may freeze either evidence package. Freeze captures a bounded,
consensus-agreed evidence snapshot and stores its SHA-256 digest; later
adjudication uses that immutable snapshot, not silently changed live pages.

A proposed verdict opens a seven-day appeal window. It becomes `FINALIZED` when
both parties acknowledge it, or when one party finalizes after the window has
closed with no appeal open -- so the favored party cannot close settlement
before the counterparty can appeal, and an unresponsive counterparty cannot
hold it open forever.

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
- Evidence URLs are fetched only during party-authorized freeze, inside a
  GenLayer strict-equality block. The bounded captured content and digest become
  the immutable adjudication package; content is explicitly treated as
  untrusted evidence, not instructions.
- Freezing binds evidence to one consensus-agreed rendering, so a source that
  renders differently for each validator (per-request timestamps, nonces,
  personalization) cannot be frozen: the freeze reverts and the package stays
  open. Each frozen item also stores up to 4,000 characters on-chain.
- Adjudication consensus is judged by settlement consequence, not by digits.
  Two validator results are equivalent only if they land in the same payment
  band under the agreement's own policy and agree on whether the confounder and
  guardrail caps apply; inside the continuous partial-payment band they must
  also be within 300 bps. Confidence and evidence-quality scores carry loose
  bounds because nothing downstream consumes them. Exact numeric agreement was
  tried first and could not reach consensus on-chain -- see `docs/smoke-test.md`.
- A verdict finalizes on both parties' acknowledgement, or on one party's
  after the seven-day appeal window closes with no appeal open. The window is a
  protocol constant measured against the VM clock, not a party-supplied
  deadline, so neither side can shorten it or stall settlement indefinitely.
- `source_host` stores the raw normalized hostname. Different subdomains may
  share an owner; LACUNA does not claim this proves independence because safe
  registrable-domain normalization needs public-suffix data.
- Canonical StudioNet deployment:
  `0x5abdf6380Faaa1f0Eb51cc666A8660D5a8Dd73a6`, running the v0.2.0
  protocol-hardening source (normalized sha256
  `d6aa8bd41ae57784c391e51c720a2516f5bcd246b37d93771e0a10f1c4640656`). Its
  schema was retrieved from the live contract through official GenLayerJS and
  is recorded in `docs/deployed-schema.json`. The Stage 9 instance at
  `0x0FA601A457a03967a5Ed008e2f82e7966392516A` is superseded and is not
  maintained; GenLayer contracts are not upgraded in place.
- No production transfer path exists. The React/TypeScript frontend in
  `frontend/` connects directly to the canonical StudioNet deployment and
  treats a write as successful only after finalized successful execution.

## Production release

- GitHub: [Chinny070/lacuna](https://github.com/Chinny070/lacuna)
- Frontend: [lacuna-ten.vercel.app](https://lacuna-ten.vercel.app)
- Network: GenLayer StudioNet, chain ID `61999`, RPC
  `https://studio.genlayer.com/api`
- Contract: `0x5abdf6380Faaa1f0Eb51cc666A8660D5a8Dd73a6`

The production site has verified read-only StudioNet access. A real
injected StudioNet-compatible wallet is still required to manually verify
signature, network-switch, and finalized write-transaction flows.

See `docs/` for constitutions, policy, evidence, security, integration,
StudioNet deployment, and the live smoke test.

## Reproducible direct tests

From a clean Python 3.12+ environment:

```bash
python -m pip install -r requirements-dev.txt
pytest tests/direct/ -v
```

`tests/direct/conftest.py` contains a Windows-only compatibility shim for the
known `genlayer-test==0.29.2` stdin temp-file unlink issue. It affects the test
harness only; it does not patch site-packages or weaken contract assertions.
