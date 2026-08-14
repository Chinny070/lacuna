# Baseline constitutions

`BaselineConstitution` records are generic and reusable. Creating the same
logical name creates a new version; the previous version becomes `INACTIVE`
but remains queryable by ID and through `get_constitution_versions(name)`.

Fields: `constitution_id`, `creator`, `name`, `version`, `primary_metric`,
`supporting_metric_schema`, `guardrail_metric_schema`, `baseline_method`,
`minimum_evidence_categories`, `minimum_independent_sources`,
`external_shock_policy`, `attribution_rules`, `falsification_rules`, `status`,
and `created_at`.

The locked constitution determines the metrics and the applicable
falsification checks: `PRE_TREND_CHECK`, `PLACEBO_WINDOW_CHECK`,
`PERSISTENCE_CHECK`, `GUARDRAIL_CHECK`, `METHODOLOGY_CONSISTENCY_CHECK`, and
`CROSS_SIGNAL_CHECK`.
