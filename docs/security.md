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
reason-code variation but requires every decision-bearing numeric field to match
exactly, so tolerated validator disagreement cannot move a settlement band or
change a confounder/guardrail cap. Performance copies baseline values from the
locked baseline exactly; refs, BPS values, reason codes, summaries, and
guardrail consistency are validated deterministically.

A proposed verdict becomes FINAL only after both the client and the contractor
call `finalize_verdict`. Either party can appeal before that, and resolving an
appeal clears both acknowledgements, so no favored party can close settlement
before the counterparty has had its opportunity to appeal.

There is no admin override, arbitrary manual baseline/verdict replacement, or
production token-transfer logic. Historical records remain queryable and final
baselines, frozen evidence, and final verdicts cannot be changed publicly.
