# Evidence model

Baseline and outcome evidence have immutable historical IDs and include source
type, validated HTTP(S) URL, normalized raw `source_host`, SHA-256 content
hash, bounded summary, metric reference, period, submitter, and status.
Outcome evidence also carries `observed_value_bps`.

Evidence uses allowlisted categories, locked-constitution metrics, matching
baseline/observation windows, duplicate-ID/content-hash/source-period checks,
and a 48-item cap per collection. Freezing moves records from `SUBMITTED` to
`FROZEN`; later submission is rejected.

Alternative explanations are independent records with type, statement,
evidence refs, affected metrics, direction, and submitter-asserted strength.
That asserted strength is never authoritative attribution.

Raw hostname is intentionally retained without heuristic domain-family
normalization. `a.example.com` and `b.example.com` can share ownership; correct
registrable-domain grouping requires public-suffix data. LACUNA preserves the
metadata and instructs GenLayer to assess source independence instead.
