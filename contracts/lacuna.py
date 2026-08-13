# { "Depends": "py-genlayer:1jb45aa8ynh2a9c9xn3b7qqh8sm5q93hwfp7jqmwsfhh8jpz09h6" }

from genlayer import *

import json
import hashlib
import re
from datetime import datetime
from urllib.parse import urlparse

# --- Status constants (spec section 15 / brief section 7) ---

AGREEMENT_STATUSES = (
    "DRAFT",
    "BASELINE_OPEN",
    "BASELINE_FROZEN",
    "BASELINE_PROPOSED",
    "BASELINE_CHALLENGED",
    "BASELINE_FINAL",
    "OBSERVING",
    "RESOLUTION_OPEN",
    "RESOLUTION_FROZEN",
    "VERDICT_PROPOSED",
    "APPEALED",
    "FINALIZED",
    "CANCELLED",
)

EVIDENCE_STATUSES = ("SUBMITTED", "FROZEN", "INVALIDATED")

BASELINE_STATUSES = ("PROPOSED", "CHALLENGED", "FINAL", "VOID")

VERDICT_STATUSES = ("PROPOSED", "APPEALED", "FINAL", "VOID")

# Evidence categories a constitution's minimum_evidence_categories may draw
# from (spec section 22). Generic on purpose -- not tied to one vertical.
EVIDENCE_CATEGORIES = frozenset(
    {
        "PUBLIC_ANALYTICS",
        "GITHUB",
        "COMMUNITY_ACTIVITY",
        "PUBLIC_ANNOUNCEMENT",
        "SECURITY_REPORT",
        "STATUS_PAGE",
        "PUBLIC_METRIC_DASHBOARD",
        "REPOSITORY_ACTIVITY",
        "MARKET_BENCHMARK",
        "PUBLIC_DATASET",
        "PUBLIC_FORUM",
        "PROJECT_DOCUMENTATION",
    }
)

# Falsification checks a constitution may require (brief section 16).
FALSIFICATION_CHECKS = frozenset(
    {
        "PRE_TREND_CHECK",
        "PLACEBO_WINDOW_CHECK",
        "PERSISTENCE_CHECK",
        "GUARDRAIL_CHECK",
        "METHODOLOGY_CONSISTENCY_CHECK",
        "CROSS_SIGNAL_CHECK",
    }
)

# --- Bounds ---

BPS_MIN = 0
BPS_MAX = 10000

TITLE_MAX_LEN = 200
OBLIGATION_MAX_LEN = 2000

NAME_MAX_LEN = 100
METRIC_NAME_MAX_LEN = 100
MAX_SCHEMA_ENTRIES = 20
METHOD_MAX_LEN = 500
SHOCK_POLICY_MAX_LEN = 500
RULE_MAX_LEN = 300
MAX_RULE_ENTRIES = 20

MIN_INDEPENDENT_SOURCES_MAX = 50

# u256 is the storage type for escrow_amount; keep a generous but bounded
# application-level ceiling well inside u256 range so obviously-wrong inputs
# (accidental extra zeros, negative-as-huge-unsigned, etc.) fail fast.
ESCROW_AMOUNT_MAX = (1 << 128) - 1

# Windows are unix-epoch seconds, deterministic integers supplied by the
# caller (no wall-clock reads inside the contract).
WINDOW_TIMESTAMP_MAX = (1 << 63) - 1

# Baseline evidence bounds (brief section 12).
EVIDENCE_ID_MAX_LEN = 100
SOURCE_URL_MAX_LEN = 500
SUMMARY_MAX_LEN = 1000
MAX_BASELINE_EVIDENCE_PER_AGREEMENT = 48

# content_hash must be a lowercase-hex sha256 digest -- deterministic,
# network-free structural validation before any adjudication (Stage 4+).
_CONTENT_HASH_RE = re.compile(r"^[0-9a-f]{64}$")


def _is_valid_address(value: str) -> bool:
    if not isinstance(value, str):
        return False
    if not value.startswith("0x") and not value.startswith("0X"):
        return False
    hex_part = value[2:]
    if len(hex_part) != 40:
        return False
    try:
        int(hex_part, 16)
    except ValueError:
        return False
    return int(hex_part, 16) != 0


def _validate_bounded_text(value: str, field_name: str, max_len: int, required: bool = True) -> None:
    if required and not value:
        raise gl.vm.UserError(f"{field_name} must not be empty")
    if value and len(value) > max_len:
        raise gl.vm.UserError(f"{field_name} must be at most {max_len} characters")


def _validate_bps(value: int, field_name: str) -> None:
    if isinstance(value, bool) or not isinstance(value, int):
        raise gl.vm.UserError(f"{field_name} must be an integer")
    if value < BPS_MIN or value > BPS_MAX:
        raise gl.vm.UserError(f"{field_name} must be between {BPS_MIN} and {BPS_MAX}")


def _validate_timestamp(value: int, field_name: str) -> None:
    if isinstance(value, bool) or not isinstance(value, int):
        raise gl.vm.UserError(f"{field_name} must be an integer unix timestamp")
    if value < 0 or value > WINDOW_TIMESTAMP_MAX:
        raise gl.vm.UserError(f"{field_name} is out of range")


def _validate_metric_schema(entries: list[str], field_name: str) -> None:
    if len(entries) > MAX_SCHEMA_ENTRIES:
        raise gl.vm.UserError(f"{field_name} must have at most {MAX_SCHEMA_ENTRIES} entries")
    if len(entries) != len(set(entries)):
        raise gl.vm.UserError(f"{field_name} must not contain duplicates")
    for entry in entries:
        _validate_bounded_text(entry, f"{field_name} entry", METRIC_NAME_MAX_LEN)


def _validate_source_url(source_url: str) -> str:
    """Deterministic, network-free structural validation of an evidence source URL."""
    if not source_url or len(source_url) > SOURCE_URL_MAX_LEN:
        raise gl.vm.UserError(f"source_url must be 1-{SOURCE_URL_MAX_LEN} characters")
    parsed = urlparse(source_url)
    if parsed.scheme not in ("http", "https"):
        raise gl.vm.UserError("source_url must use http or https")
    if not parsed.netloc:
        raise gl.vm.UserError("source_url is missing a host")
    return parsed.netloc.lower()


def _validate_content_hash(content_hash: str) -> None:
    if not _CONTENT_HASH_RE.fullmatch(content_hash or ""):
        raise gl.vm.UserError("content_hash must be a 64-character lowercase hex sha256 digest")


class Lacuna(gl.Contract):
    # PerformanceAgreement
    agreements: TreeMap[str, str]
    agreement_count: u256

    # BaselineConstitution (id -> record) + name -> [constitution_id, ...] versions
    constitutions: TreeMap[str, str]
    constitution_count: u256
    constitution_versions: TreeMap[str, str]

    # BaselineEvidence (id -> record) + agreement -> [evidence_id, ...]
    baseline_evidence: TreeMap[str, str]
    baseline_evidence_count: u256
    agreement_baseline_evidence_ids: TreeMap[str, str]

    # CounterfactualBaseline
    baselines: TreeMap[str, str]
    baseline_count: u256

    # BaselineChallenge (id -> record) + baseline -> [challenge_id, ...]
    baseline_challenges: TreeMap[str, str]
    baseline_challenge_count: u256
    baseline_challenge_ids: TreeMap[str, str]

    # OutcomeEvidence (id -> record) + agreement -> [evidence_id, ...]
    outcome_evidence: TreeMap[str, str]
    outcome_evidence_count: u256
    agreement_outcome_evidence_ids: TreeMap[str, str]

    # AlternativeExplanation (id -> record) + agreement -> [explanation_id, ...]
    alternative_explanations: TreeMap[str, str]
    alternative_explanation_count: u256
    agreement_explanation_ids: TreeMap[str, str]

    # AttributionVerdict
    verdicts: TreeMap[str, str]
    verdict_count: u256

    # SettlementPolicy (id -> record) + name -> [policy_id, ...] versions
    settlement_policies: TreeMap[str, str]
    settlement_policy_count: u256
    settlement_policy_versions: TreeMap[str, str]

    # PerformanceAppeal (id -> record) + verdict -> [appeal_id, ...]
    appeals: TreeMap[str, str]
    appeal_count: u256
    verdict_appeal_ids: TreeMap[str, str]

    def __init__(self):
        self.agreement_count = u256(0)
        self.constitution_count = u256(0)
        self.baseline_evidence_count = u256(0)
        self.baseline_count = u256(0)
        self.baseline_challenge_count = u256(0)
        self.outcome_evidence_count = u256(0)
        self.alternative_explanation_count = u256(0)
        self.verdict_count = u256(0)
        self.settlement_policy_count = u256(0)
        self.appeal_count = u256(0)

    # =========================================================
    # PerformanceAgreement (spec section 14 / brief section 4+7)
    # =========================================================

    @gl.public.write
    def create_agreement(
        self,
        agreement_id: str,
        client: str,
        contractor: str,
        title: str,
        obligation: str,
        constitution_id: str,
        settlement_policy_id: str,
        baseline_window_start: int,
        baseline_window_end: int,
        observation_window_start: int,
        observation_window_end: int,
        escrow_amount: int,
    ) -> str:
        if not agreement_id or len(agreement_id) > NAME_MAX_LEN:
            raise gl.vm.UserError(f"agreement_id must be 1-{NAME_MAX_LEN} characters")
        if agreement_id in self.agreements:
            raise gl.vm.UserError("Agreement ID already exists")

        _validate_bounded_text(title, "title", TITLE_MAX_LEN)
        _validate_bounded_text(obligation, "obligation", OBLIGATION_MAX_LEN)

        if not _is_valid_address(client):
            raise gl.vm.UserError("client must be a valid, non-zero address")
        if not _is_valid_address(contractor):
            raise gl.vm.UserError("contractor must be a valid, non-zero address")

        if constitution_id not in self.constitutions:
            raise gl.vm.UserError("constitution_id does not exist")
        constitution = json.loads(self.constitutions[constitution_id])
        if constitution["status"] != "ACTIVE":
            raise gl.vm.UserError("constitution must be ACTIVE")

        if settlement_policy_id not in self.settlement_policies:
            raise gl.vm.UserError("settlement_policy_id does not exist")
        settlement_policy = json.loads(self.settlement_policies[settlement_policy_id])
        if settlement_policy["status"] != "ACTIVE":
            raise gl.vm.UserError("settlement_policy must be ACTIVE")

        _validate_timestamp(baseline_window_start, "baseline_window_start")
        _validate_timestamp(baseline_window_end, "baseline_window_end")
        _validate_timestamp(observation_window_start, "observation_window_start")
        _validate_timestamp(observation_window_end, "observation_window_end")

        if baseline_window_start >= baseline_window_end:
            raise gl.vm.UserError("baseline_window_start must be before baseline_window_end")
        if observation_window_start >= observation_window_end:
            raise gl.vm.UserError("observation_window_start must be before observation_window_end")
        if baseline_window_end > observation_window_start:
            raise gl.vm.UserError("baseline window must finish before observation window begins")

        if isinstance(escrow_amount, bool) or not isinstance(escrow_amount, int):
            raise gl.vm.UserError("escrow_amount must be an integer")
        if escrow_amount < 0 or escrow_amount > ESCROW_AMOUNT_MAX:
            raise gl.vm.UserError(f"escrow_amount must be between 0 and {ESCROW_AMOUNT_MAX}")

        record = {
            "agreement_id": agreement_id,
            "client": client,
            "contractor": contractor,
            "title": title,
            "obligation": obligation,
            "constitution_id": constitution_id,
            "settlement_policy_id": settlement_policy_id,
            "baseline_window_start": baseline_window_start,
            "baseline_window_end": baseline_window_end,
            "observation_window_start": observation_window_start,
            "observation_window_end": observation_window_end,
            "status": "DRAFT",
            "escrow_amount": escrow_amount,
            "baseline_id": "",
            "verdict_id": "",
            "appeal_id": "",
            "created_by": gl.message.sender_address.as_hex,
            "created_at": datetime.now().isoformat(),
        }
        self.agreements[agreement_id] = json.dumps(record)
        self.agreement_baseline_evidence_ids[agreement_id] = json.dumps([])
        self.agreement_outcome_evidence_ids[agreement_id] = json.dumps([])
        self.agreement_explanation_ids[agreement_id] = json.dumps([])
        self.agreement_count = u256(int(self.agreement_count) + 1)
        return agreement_id

    @gl.public.view
    def get_agreement(self, agreement_id: str) -> str:
        if agreement_id not in self.agreements:
            raise gl.vm.UserError("Agreement not found")
        return self.agreements[agreement_id]

    @gl.public.view
    def list_agreements(self) -> str:
        result = []
        for agreement_id in self.agreements:
            result.append(json.loads(self.agreements[agreement_id]))
        return json.dumps(result)

    # =========================================================
    # BaselineConstitution (spec section 14/6 / brief section 4+8)
    # =========================================================

    @gl.public.write
    def create_baseline_constitution(
        self,
        name: str,
        primary_metric: str,
        supporting_metric_schema: list[str],
        guardrail_metric_schema: list[str],
        baseline_method: str,
        minimum_evidence_categories: list[str],
        minimum_independent_sources: int,
        external_shock_policy: str,
        attribution_rules: list[str],
        falsification_rules: list[str],
    ) -> str:
        _validate_bounded_text(name, "name", NAME_MAX_LEN)
        _validate_bounded_text(primary_metric, "primary_metric", METRIC_NAME_MAX_LEN)
        _validate_bounded_text(baseline_method, "baseline_method", METHOD_MAX_LEN)
        _validate_bounded_text(external_shock_policy, "external_shock_policy", SHOCK_POLICY_MAX_LEN)

        _validate_metric_schema(supporting_metric_schema, "supporting_metric_schema")
        _validate_metric_schema(guardrail_metric_schema, "guardrail_metric_schema")

        if not minimum_evidence_categories:
            raise gl.vm.UserError("minimum_evidence_categories must not be empty")
        if len(minimum_evidence_categories) != len(set(minimum_evidence_categories)):
            raise gl.vm.UserError("minimum_evidence_categories must not contain duplicates")
        for category in minimum_evidence_categories:
            if category not in EVIDENCE_CATEGORIES:
                allowed = ", ".join(sorted(EVIDENCE_CATEGORIES))
                raise gl.vm.UserError(f"minimum_evidence_categories entries must be one of: {allowed}")

        if isinstance(minimum_independent_sources, bool) or not isinstance(
            minimum_independent_sources, int
        ):
            raise gl.vm.UserError("minimum_independent_sources must be an integer")
        if minimum_independent_sources < 1 or minimum_independent_sources > MIN_INDEPENDENT_SOURCES_MAX:
            raise gl.vm.UserError(
                f"minimum_independent_sources must be between 1 and {MIN_INDEPENDENT_SOURCES_MAX}"
            )

        if not attribution_rules:
            raise gl.vm.UserError("attribution_rules must not be empty")
        if len(attribution_rules) > MAX_RULE_ENTRIES:
            raise gl.vm.UserError(f"attribution_rules must have at most {MAX_RULE_ENTRIES} entries")
        for rule in attribution_rules:
            _validate_bounded_text(rule, "attribution_rules entry", RULE_MAX_LEN)

        if not falsification_rules:
            raise gl.vm.UserError("falsification_rules must not be empty")
        if len(falsification_rules) != len(set(falsification_rules)):
            raise gl.vm.UserError("falsification_rules must not contain duplicates")
        for check in falsification_rules:
            if check not in FALSIFICATION_CHECKS:
                allowed = ", ".join(sorted(FALSIFICATION_CHECKS))
                raise gl.vm.UserError(f"falsification_rules entries must be one of: {allowed}")

        existing_ids = json.loads(self.constitution_versions.get(name, "[]"))
        version = len(existing_ids) + 1

        now_iso = datetime.now().isoformat()
        seed = f"{name}|{version}|{now_iso}|{int(self.constitution_count)}"
        constitution_id = "constitution-" + hashlib.sha256(seed.encode()).hexdigest()[:16]
        if constitution_id in self.constitutions:
            raise gl.vm.UserError("Constitution ID collision, please retry")

        # A new version of an existing named constitution supersedes it: only
        # the newest version of a given name is ACTIVE. Older versions become
        # INACTIVE but are never deleted or mutated beyond this status flip,
        # so they remain queryable by id for history (spec section 6/13).
        if existing_ids:
            previous_id = existing_ids[-1]
            previous = json.loads(self.constitutions[previous_id])
            previous["status"] = "INACTIVE"
            self.constitutions[previous_id] = json.dumps(previous)

        record = {
            "constitution_id": constitution_id,
            "creator": gl.message.sender_address.as_hex,
            "name": name,
            "version": version,
            "primary_metric": primary_metric,
            "supporting_metric_schema": supporting_metric_schema,
            "guardrail_metric_schema": guardrail_metric_schema,
            "baseline_method": baseline_method,
            "minimum_evidence_categories": minimum_evidence_categories,
            "minimum_independent_sources": minimum_independent_sources,
            "external_shock_policy": external_shock_policy,
            "attribution_rules": attribution_rules,
            "falsification_rules": falsification_rules,
            "status": "ACTIVE",
            "created_at": now_iso,
        }
        self.constitutions[constitution_id] = json.dumps(record)

        existing_ids.append(constitution_id)
        self.constitution_versions[name] = json.dumps(existing_ids)
        self.constitution_count = u256(int(self.constitution_count) + 1)

        return constitution_id

    @gl.public.view
    def get_baseline_constitution(self, constitution_id: str) -> str:
        if constitution_id not in self.constitutions:
            raise gl.vm.UserError("Constitution not found")
        return self.constitutions[constitution_id]

    @gl.public.view
    def get_constitution_versions(self, name: str) -> str:
        return self.constitution_versions.get(name, "[]")

    @gl.public.view
    def list_constitutions(self) -> str:
        result = []
        for constitution_id in self.constitutions:
            result.append(json.loads(self.constitutions[constitution_id]))
        return json.dumps(result)

    # =========================================================
    # SettlementPolicy (spec section 14/20 / brief section 4+18)
    # =========================================================

    @gl.public.write
    def create_settlement_policy(
        self,
        name: str,
        minimum_performance_bps: int,
        full_payment_threshold_bps: int,
        bonus_threshold_bps: int,
        bonus_cap_bps: int,
        max_unresolved_confounder_bps: int,
        guardrail_failure_cap_bps: int,
    ) -> str:
        _validate_bounded_text(name, "name", NAME_MAX_LEN)

        _validate_bps(minimum_performance_bps, "minimum_performance_bps")
        _validate_bps(full_payment_threshold_bps, "full_payment_threshold_bps")
        _validate_bps(bonus_threshold_bps, "bonus_threshold_bps")
        _validate_bps(bonus_cap_bps, "bonus_cap_bps")
        _validate_bps(max_unresolved_confounder_bps, "max_unresolved_confounder_bps")
        _validate_bps(guardrail_failure_cap_bps, "guardrail_failure_cap_bps")

        if minimum_performance_bps > full_payment_threshold_bps:
            raise gl.vm.UserError(
                "minimum_performance_bps must be <= full_payment_threshold_bps"
            )
        if full_payment_threshold_bps > bonus_threshold_bps:
            raise gl.vm.UserError(
                "full_payment_threshold_bps must be <= bonus_threshold_bps"
            )

        existing_ids = json.loads(self.settlement_policy_versions.get(name, "[]"))
        version = len(existing_ids) + 1

        now_iso = datetime.now().isoformat()
        seed = f"{name}|{version}|{now_iso}|{int(self.settlement_policy_count)}"
        policy_id = "policy-" + hashlib.sha256(seed.encode()).hexdigest()[:16]
        if policy_id in self.settlement_policies:
            raise gl.vm.UserError("Settlement policy ID collision, please retry")

        # Same supersede-by-name versioning as constitutions: older versions
        # flip to INACTIVE and stay queryable, never deleted or rewritten.
        if existing_ids:
            previous_id = existing_ids[-1]
            previous = json.loads(self.settlement_policies[previous_id])
            previous["status"] = "INACTIVE"
            self.settlement_policies[previous_id] = json.dumps(previous)

        record = {
            "policy_id": policy_id,
            "creator": gl.message.sender_address.as_hex,
            "name": name,
            "version": version,
            "minimum_performance_bps": minimum_performance_bps,
            "full_payment_threshold_bps": full_payment_threshold_bps,
            "bonus_threshold_bps": bonus_threshold_bps,
            "bonus_cap_bps": bonus_cap_bps,
            "max_unresolved_confounder_bps": max_unresolved_confounder_bps,
            "guardrail_failure_cap_bps": guardrail_failure_cap_bps,
            "status": "ACTIVE",
            "created_at": now_iso,
        }
        self.settlement_policies[policy_id] = json.dumps(record)

        existing_ids.append(policy_id)
        self.settlement_policy_versions[name] = json.dumps(existing_ids)
        self.settlement_policy_count = u256(int(self.settlement_policy_count) + 1)

        return policy_id

    @gl.public.view
    def get_settlement_policy(self, policy_id: str) -> str:
        if policy_id not in self.settlement_policies:
            raise gl.vm.UserError("Settlement policy not found")
        return self.settlement_policies[policy_id]

    @gl.public.view
    def get_settlement_policy_versions(self, name: str) -> str:
        return self.settlement_policy_versions.get(name, "[]")

    @gl.public.view
    def list_settlement_policies(self) -> str:
        result = []
        for policy_id in self.settlement_policies:
            result.append(json.loads(self.settlement_policies[policy_id]))
        return json.dumps(result)

    # =========================================================
    # BaselineEvidence (spec section 14 / brief section 4+12)
    # =========================================================

    @gl.public.write
    def submit_baseline_evidence(
        self,
        evidence_id: str,
        agreement_id: str,
        source_type: str,
        source_url: str,
        content_hash: str,
        summary: str,
        metric_ref: str,
        period_start: int,
        period_end: int,
    ) -> str:
        if not evidence_id or len(evidence_id) > EVIDENCE_ID_MAX_LEN:
            raise gl.vm.UserError(f"evidence_id must be 1-{EVIDENCE_ID_MAX_LEN} characters")
        if evidence_id in self.baseline_evidence:
            raise gl.vm.UserError("Baseline evidence ID already exists")

        if agreement_id not in self.agreements:
            raise gl.vm.UserError("Agreement not found")
        agreement = json.loads(self.agreements[agreement_id])

        # Baseline evidence collection is open from the moment an agreement
        # is created (DRAFT) up through the explicit BASELINE_OPEN state;
        # the first submission lazily advances DRAFT -> BASELINE_OPEN, the
        # same pattern reality_lock.py uses for OPEN -> EVIDENCE_SUBMITTED.
        if agreement["status"] not in ("DRAFT", "BASELINE_OPEN"):
            raise gl.vm.UserError(
                "Agreement must be in DRAFT or BASELINE_OPEN status to accept baseline evidence"
            )

        sender = gl.message.sender_address.as_hex
        if sender.lower() not in (agreement["client"].lower(), agreement["contractor"].lower()):
            raise gl.vm.UserError(
                "Only the agreement's client or contractor may submit baseline evidence"
            )

        if source_type not in EVIDENCE_CATEGORIES:
            allowed = ", ".join(sorted(EVIDENCE_CATEGORIES))
            raise gl.vm.UserError(f"source_type must be one of: {allowed}")

        source_host = _validate_source_url(source_url)
        _validate_content_hash(content_hash)
        _validate_bounded_text(summary, "summary", SUMMARY_MAX_LEN)

        constitution = json.loads(self.constitutions[agreement["constitution_id"]])
        allowed_metrics = (
            {constitution["primary_metric"]}
            | set(constitution["supporting_metric_schema"])
            | set(constitution["guardrail_metric_schema"])
        )
        if metric_ref not in allowed_metrics:
            raise gl.vm.UserError(
                "metric_ref must match the agreement's constitution "
                "(primary, supporting, or guardrail metric)"
            )

        _validate_timestamp(period_start, "period_start")
        _validate_timestamp(period_end, "period_end")
        if period_start >= period_end:
            raise gl.vm.UserError("period_start must be before period_end")
        if period_start < agreement["baseline_window_start"] or period_end > agreement["baseline_window_end"]:
            raise gl.vm.UserError(
                "Evidence period must fall entirely within the agreement's baseline window"
            )

        evidence_ids = json.loads(self.agreement_baseline_evidence_ids[agreement_id])
        if len(evidence_ids) >= MAX_BASELINE_EVIDENCE_PER_AGREEMENT:
            raise gl.vm.UserError(
                f"Baseline evidence cap reached ({MAX_BASELINE_EVIDENCE_PER_AGREEMENT})"
            )

        norm_url = source_url.strip().lower()
        for existing_id in evidence_ids:
            existing = json.loads(self.baseline_evidence[existing_id])
            if existing["content_hash"] == content_hash:
                raise gl.vm.UserError("Duplicate evidence: content_hash already submitted for this agreement")
            existing_url = existing["source_url"].strip().lower()
            if existing_url == norm_url and existing["period_start"] == period_start and existing["period_end"] == period_end:
                raise gl.vm.UserError("Duplicate evidence: same source_url and period already submitted")

        record = {
            "evidence_id": evidence_id,
            "agreement_id": agreement_id,
            "submitter": sender,
            "source_type": source_type,
            "source_url": source_url,
            "source_host": source_host,
            "content_hash": content_hash,
            "summary": summary,
            "metric_ref": metric_ref,
            "period_start": period_start,
            "period_end": period_end,
            "submitted_at": datetime.now().isoformat(),
            "status": "SUBMITTED",
        }
        self.baseline_evidence[evidence_id] = json.dumps(record)

        evidence_ids.append(evidence_id)
        self.agreement_baseline_evidence_ids[agreement_id] = json.dumps(evidence_ids)

        self.baseline_evidence_count = u256(int(self.baseline_evidence_count) + 1)

        if agreement["status"] == "DRAFT":
            agreement["status"] = "BASELINE_OPEN"
            self.agreements[agreement_id] = json.dumps(agreement)

        return evidence_id

    @gl.public.view
    def get_baseline_evidence(self, evidence_id: str) -> str:
        if evidence_id not in self.baseline_evidence:
            raise gl.vm.UserError("Baseline evidence not found")
        return self.baseline_evidence[evidence_id]

    @gl.public.view
    def list_baseline_evidence(self, agreement_id: str) -> str:
        if agreement_id not in self.agreements:
            raise gl.vm.UserError("Agreement not found")
        evidence_ids = json.loads(self.agreement_baseline_evidence_ids[agreement_id])
        result = []
        for evidence_id in evidence_ids:
            result.append(json.loads(self.baseline_evidence[evidence_id]))
        return json.dumps(result)

    @gl.public.write
    def freeze_baseline_evidence(self, agreement_id: str) -> str:
        if agreement_id not in self.agreements:
            raise gl.vm.UserError("Agreement not found")
        agreement = json.loads(self.agreements[agreement_id])

        if agreement["status"] != "BASELINE_OPEN":
            raise gl.vm.UserError("Agreement must be in BASELINE_OPEN status to freeze baseline evidence")

        constitution = json.loads(self.constitutions[agreement["constitution_id"]])
        minimum_independent_sources = constitution["minimum_independent_sources"]

        evidence_ids = json.loads(self.agreement_baseline_evidence_ids[agreement_id])
        evidence_records = [json.loads(self.baseline_evidence[eid]) for eid in evidence_ids]

        if len(evidence_records) < minimum_independent_sources:
            raise gl.vm.UserError(
                f"Insufficient baseline evidence: at least {minimum_independent_sources} "
                f"item(s) required, found {len(evidence_records)}"
            )

        present_categories = {record["source_type"] for record in evidence_records}
        required_categories = set(constitution["minimum_evidence_categories"])
        missing_categories = required_categories - present_categories
        if missing_categories:
            raise gl.vm.UserError(
                "Insufficient evidence categories, missing: " + ", ".join(sorted(missing_categories))
            )

        independent_hosts = {record["source_host"] for record in evidence_records}
        if len(independent_hosts) < minimum_independent_sources:
            raise gl.vm.UserError(
                f"Insufficient independent sources: at least {minimum_independent_sources} "
                f"distinct source host(s) required, found {len(independent_hosts)}"
            )

        for record in evidence_records:
            record["status"] = "FROZEN"
            self.baseline_evidence[record["evidence_id"]] = json.dumps(record)

        agreement["status"] = "BASELINE_FROZEN"
        self.agreements[agreement_id] = json.dumps(agreement)

        return agreement_id
