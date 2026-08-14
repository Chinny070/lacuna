# Security model

Deterministic checks cover authorization, lifecycle state, field bounds, BPS
ranges, windows, URL structure, SHA-256 hashes, metric references, evidence
caps, duplicate IDs/content hashes, and duplicate source-period submissions.
Challenge and appeal evidence refs must belong to their frozen package. One
open challenge per proposed baseline and one open appeal per current verdict
are permitted.

All GenLayer adjudication output is comparative-consensus output followed by
strict exact-schema parsing. Unknown top-level fields are rejected for baseline,
challenge, performance, and appeal results. Performance copies baseline values
from the locked baseline exactly; refs, BPS values, reason codes, summaries,
and guardrail consistency are validated deterministically.

Only stored validated evidence URLs can be fetched. Their content is bounded,
delimited, and marked untrusted; prompts say to ignore embedded instructions.
There is no admin override, arbitrary manual baseline/verdict replacement, or
production token-transfer logic. Historical records remain queryable and final
baselines, frozen evidence, and final verdicts cannot be changed publicly.
