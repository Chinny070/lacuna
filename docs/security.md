# Security model

Deterministic checks cover authorization, lifecycle state, field bounds, BPS
ranges, windows, URL structure, SHA-256 hashes, metric references, evidence
caps, duplicate IDs/content hashes, and duplicate source-period submissions.
Challenge and appeal evidence refs must belong to their frozen package. One
open challenge per proposed baseline and one open appeal per current verdict
are permitted.

Every agreement-scoped write is restricted to that agreement's client or
contractor. That now includes both freeze transitions: an unrelated caller
cannot close another agreement's baseline or resolution package. Constitutions
and settlement policies stay openly publishable because they are reusable rule
sets that bind nobody until an agreement references them.

Evidence is fetched exactly once, during a party-authorized freeze, inside a
GenLayer strict-equality block. Freeze stores the bounded rendered text and its
SHA-256 digest on the evidence record and reverts if any source cannot be
snapshotted by consensus. Adjudication re-verifies the stored digest against
the stored content before the text reaches a prompt, so a page that changes
after freeze cannot silently become the historical evidence, and a tampered
snapshot reverts instead of being judged. Content is bounded, delimited, and
marked untrusted; prompts say to ignore embedded instructions.

All GenLayer adjudication output is comparative-consensus output followed by
strict exact-schema parsing. Unknown top-level fields are rejected for baseline,
challenge, performance, and appeal results. Equivalence permits wording and
reason-code variation, and is judged on settlement consequence rather than on
digits: verdict results are equivalent only when performance_bps falls in the
same payment band under the agreement's policy (and within 300 bps inside the
continuous partial band), and both agree on whether the unresolved-confounder
and guardrail caps apply. Values on opposite sides of a threshold are never
equivalent. Confidence and evidence-quality scores carry loose bounds because
they enter no settlement arithmetic and gate no threshold. Baseline evaluation
carries a bounded tolerance because a proposed baseline locks only once both
parties accept it. Performance copies baseline values from the
locked baseline exactly; refs, BPS values, reason codes, summaries, and
guardrail consistency are validated deterministically.

Proposing a verdict stamps an authoritative appeal deadline
(`appeal_window_ends_at`, `APPEAL_WINDOW_SECONDS` = 7 days) on the agreement.
`finalize_verdict` reaches FINAL by exactly two routes: both the client and the
contractor have called it, or one party calls it after that deadline has
passed. Both routes still refuse to finalize while an appeal is unresolved.
Resolving an appeal clears both acknowledgements and restarts the window for
the verdict that survives, and a voided verdict clears it entirely. So a
favored party cannot close settlement before the counterparty's window, and a
counterparty that never responds cannot strand it.

The deadline is compared against `datetime.now()`, which the VM supplies per
transaction -- the same clock the contract already relies on to derive
consistent verdict IDs. It is a protocol constant, never a party-supplied
value, so neither side can shorten its counterparty's window.

There is no admin override, arbitrary manual baseline/verdict replacement, or
production token-transfer logic. Historical records remain queryable and final
baselines, frozen evidence, and final verdicts cannot be changed publicly.
