# Evidence model

Baseline and outcome evidence have immutable historical IDs and include source
type, validated HTTP(S) URL, normalized raw `source_host`, SHA-256 content
hash, bounded summary, metric reference, period, submitter, and status.
Outcome evidence also carries `observed_value_bps`.

Evidence uses allowlisted categories, locked-constitution metrics, matching
baseline/observation windows, duplicate-ID/content-hash/source-period checks,
and a 48-item cap per collection. Freezing moves records from `SUBMITTED` to
`FROZEN`; later submission is rejected.

Only an agreement party may freeze. Freeze renders every stored source URL once
inside a GenLayer strict-equality block and writes three fields per record:
`frozen_content` (the bounded consensus-agreed page text), `frozen_content_hash`
(its SHA-256 digest), and `submitted_content_hash` (the submitter's original
claim, preserved for traceability). `content_hash` is replaced by the verified
snapshot digest, so the authoritative hash describes content the protocol
actually saw rather than a value the submitter asserted. If any source cannot be
snapshotted by consensus, the whole freeze reverts and the package stays open.

Adjudication reads only `frozen_content`, and re-checks it against
`frozen_content_hash` first; a mismatch reverts. Before freeze the submitted
hash serves only as a duplicate-submission identifier -- it is never treated as
proof of what a page contained.

Alternative explanations are independent records with type, statement,
evidence refs, affected metrics, direction, and submitter-asserted strength.
That asserted strength is never authoritative attribution.

Raw hostname is intentionally retained without heuristic domain-family
normalization. `a.example.com` and `b.example.com` can share ownership; correct
registrable-domain grouping requires public-suffix data. LACUNA preserves the
metadata and instructs GenLayer to assess source independence instead.
