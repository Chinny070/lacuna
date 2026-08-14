# Settlement policies

Policies are reusable and versioned. Prior versions become `INACTIVE` but are
preserved through `get_settlement_policy` and
`get_settlement_policy_versions(name)`.

Fields: `policy_id`, `creator`, `name`, `version`,
`minimum_performance_bps`, `full_payment_threshold_bps`,
`bonus_threshold_bps`, `bonus_cap_bps`, `max_unresolved_confounder_bps`,
`guardrail_failure_cap_bps`, `status`, and `created_at`.

All BPS values are integers in `[0, 10000]`, with minimum ≤ full threshold ≤
bonus threshold. Preview uses integer-only arithmetic: zero below minimum,
linear escrow scaling to full threshold, and full escrow thereafter.
Confounder/guardrail limits cap effective performance. Bonus is advisory and
excluded from final payment because no funded bonus pool exists.
