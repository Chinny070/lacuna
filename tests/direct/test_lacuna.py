import hashlib
import json
from datetime import datetime, timedelta

import pytest


def as_hex(address) -> str:
    """direct_alice/direct_bob/direct_charlie fixtures yield raw-ish address
    objects; contract-side Address.as_hex is '0x' + hex. Normalize here."""
    return address.as_hex if hasattr(address, "as_hex") else "0x" + address.hex()


VALID_CLIENT = "0x" + "1" * 40
VALID_CONTRACTOR = "0x" + "2" * 40
ZERO_ADDRESS = "0x" + "0" * 40

BASELINE_START = 1_700_000_000
BASELINE_END = 1_700_600_000
OBSERVATION_START = 1_700_600_000
OBSERVATION_END = 1_701_200_000


def make_constitution(lacuna, name="Community Health v1"):
    return lacuna.create_baseline_constitution(
        name,
        "monthly_churn_bps",
        ["disputes", "escalations"],
        ["contributor_retention", "member_activity"],
        "historical_trend_with_benchmark",
        ["PUBLIC_ANALYTICS", "COMMUNITY_ACTIVITY"],
        2,
        "Exclude windows overlapping a declared market-wide shock.",
        ["Prefer explicit later evidence over earlier drafts."],
        ["PRE_TREND_CHECK", "GUARDRAIL_CHECK"],
    )


def make_policy(lacuna, name="Standard Settlement v1"):
    return lacuna.create_settlement_policy(
        name,
        2000,
        6000,
        8000,
        1500,
        3000,
        4000,
    )


def create_agreement(
    lacuna,
    agreement_id="AGR-1",
    constitution_id=None,
    policy_id=None,
    client=VALID_CLIENT,
    contractor=VALID_CONTRACTOR,
    title="Maintain community stability",
    obligation="Keep churn and disputes low for six months.",
    baseline_window_start=BASELINE_START,
    baseline_window_end=BASELINE_END,
    observation_window_start=OBSERVATION_START,
    observation_window_end=OBSERVATION_END,
    escrow_amount=10_000,
):
    if constitution_id is None:
        constitution_id = make_constitution(lacuna)
    if policy_id is None:
        policy_id = make_policy(lacuna)
    return lacuna.create_agreement(
        agreement_id,
        client,
        contractor,
        title,
        obligation,
        constitution_id,
        policy_id,
        baseline_window_start,
        baseline_window_end,
        observation_window_start,
        observation_window_end,
        escrow_amount,
    ), constitution_id, policy_id


# =========================================================
# PerformanceAgreement
# =========================================================


def test_deploy_and_initial_storage_is_empty(direct_deploy):
    lacuna = direct_deploy("contracts/lacuna.py")
    assert lacuna.agreement_count == 0
    assert lacuna.constitution_count == 0
    assert lacuna.baseline_count == 0
    assert lacuna.verdict_count == 0
    assert lacuna.settlement_policy_count == 0
    assert lacuna.appeal_count == 0
    assert json.loads(lacuna.list_agreements()) == []
    assert json.loads(lacuna.list_constitutions()) == []
    assert json.loads(lacuna.list_settlement_policies()) == []


def test_create_agreement_and_read_back(direct_deploy):
    lacuna = direct_deploy("contracts/lacuna.py")
    agreement_id, constitution_id, policy_id = create_agreement(lacuna)

    assert agreement_id == "AGR-1"
    assert lacuna.agreement_count == 1

    record = json.loads(lacuna.get_agreement("AGR-1"))
    assert record["agreement_id"] == "AGR-1"
    assert record["status"] == "DRAFT"
    assert record["title"] == "Maintain community stability"
    assert record["client"] == VALID_CLIENT
    assert record["contractor"] == VALID_CONTRACTOR
    assert record["constitution_id"] == constitution_id
    assert record["settlement_policy_id"] == policy_id
    assert record["baseline_window_start"] == BASELINE_START
    assert record["baseline_window_end"] == BASELINE_END
    assert record["observation_window_start"] == OBSERVATION_START
    assert record["observation_window_end"] == OBSERVATION_END
    assert record["escrow_amount"] == 10_000

    listed = json.loads(lacuna.list_agreements())
    assert len(listed) == 1
    assert listed[0]["agreement_id"] == "AGR-1"


def test_create_agreement_rejects_duplicate_id(direct_deploy):
    lacuna = direct_deploy("contracts/lacuna.py")
    create_agreement(lacuna, agreement_id="AGR-1")

    constitution_id = json.loads(lacuna.list_constitutions())[0]["constitution_id"]
    policy_id = json.loads(lacuna.list_settlement_policies())[0]["policy_id"]

    with pytest.raises(Exception, match="already exists"):
        lacuna.create_agreement(
            "AGR-1",
            VALID_CLIENT,
            VALID_CONTRACTOR,
            "Title",
            "Obligation",
            constitution_id,
            policy_id,
            BASELINE_START,
            BASELINE_END,
            OBSERVATION_START,
            OBSERVATION_END,
            10_000,
        )


def test_get_agreement_missing_raises(direct_deploy):
    lacuna = direct_deploy("contracts/lacuna.py")
    with pytest.raises(Exception, match="not found"):
        lacuna.get_agreement("does-not-exist")


def test_list_agreements_returns_all_stored_ids(direct_deploy):
    lacuna = direct_deploy("contracts/lacuna.py")
    constitution_id = make_constitution(lacuna)
    policy_id = make_policy(lacuna)
    create_agreement(lacuna, agreement_id="AGR-1", constitution_id=constitution_id, policy_id=policy_id)
    create_agreement(lacuna, agreement_id="AGR-2", constitution_id=constitution_id, policy_id=policy_id)

    assert lacuna.agreement_count == 2
    listed_ids = {row["agreement_id"] for row in json.loads(lacuna.list_agreements())}
    assert listed_ids == {"AGR-1", "AGR-2"}


def test_create_agreement_rejects_zero_address_client(direct_deploy):
    lacuna = direct_deploy("contracts/lacuna.py")
    with pytest.raises(Exception, match="client"):
        create_agreement(lacuna, client=ZERO_ADDRESS)


def test_create_agreement_rejects_invalid_address_contractor(direct_deploy):
    lacuna = direct_deploy("contracts/lacuna.py")
    with pytest.raises(Exception, match="contractor"):
        create_agreement(lacuna, contractor="not-an-address")


def test_create_agreement_rejects_unknown_constitution(direct_deploy):
    lacuna = direct_deploy("contracts/lacuna.py")
    policy_id = make_policy(lacuna)
    with pytest.raises(Exception, match="constitution_id"):
        lacuna.create_agreement(
            "AGR-1",
            VALID_CLIENT,
            VALID_CONTRACTOR,
            "Title",
            "Obligation",
            "does-not-exist",
            policy_id,
            BASELINE_START,
            BASELINE_END,
            OBSERVATION_START,
            OBSERVATION_END,
            10_000,
        )


def test_create_agreement_rejects_inactive_constitution(direct_deploy):
    lacuna = direct_deploy("contracts/lacuna.py")
    old_id = make_constitution(lacuna, name="Same Name")
    make_constitution(lacuna, name="Same Name")  # supersedes old_id -> INACTIVE
    policy_id = make_policy(lacuna)

    with pytest.raises(Exception, match="ACTIVE"):
        lacuna.create_agreement(
            "AGR-1",
            VALID_CLIENT,
            VALID_CONTRACTOR,
            "Title",
            "Obligation",
            old_id,
            policy_id,
            BASELINE_START,
            BASELINE_END,
            OBSERVATION_START,
            OBSERVATION_END,
            10_000,
        )


def test_create_agreement_rejects_unknown_settlement_policy(direct_deploy):
    lacuna = direct_deploy("contracts/lacuna.py")
    constitution_id = make_constitution(lacuna)
    with pytest.raises(Exception, match="settlement_policy_id"):
        lacuna.create_agreement(
            "AGR-1",
            VALID_CLIENT,
            VALID_CONTRACTOR,
            "Title",
            "Obligation",
            constitution_id,
            "does-not-exist",
            BASELINE_START,
            BASELINE_END,
            OBSERVATION_START,
            OBSERVATION_END,
            10_000,
        )


def test_create_agreement_rejects_inactive_settlement_policy(direct_deploy):
    lacuna = direct_deploy("contracts/lacuna.py")
    constitution_id = make_constitution(lacuna)
    old_id = make_policy(lacuna, name="Same Policy")
    make_policy(lacuna, name="Same Policy")  # supersedes old_id -> INACTIVE

    with pytest.raises(Exception, match="ACTIVE"):
        lacuna.create_agreement(
            "AGR-1",
            VALID_CLIENT,
            VALID_CONTRACTOR,
            "Title",
            "Obligation",
            constitution_id,
            old_id,
            BASELINE_START,
            BASELINE_END,
            OBSERVATION_START,
            OBSERVATION_END,
            10_000,
        )


def test_create_agreement_rejects_inverted_baseline_window(direct_deploy):
    lacuna = direct_deploy("contracts/lacuna.py")
    with pytest.raises(Exception, match="baseline_window"):
        create_agreement(lacuna, baseline_window_start=BASELINE_END, baseline_window_end=BASELINE_START)


def test_create_agreement_rejects_inverted_observation_window(direct_deploy):
    lacuna = direct_deploy("contracts/lacuna.py")
    with pytest.raises(Exception, match="observation_window"):
        create_agreement(
            lacuna,
            observation_window_start=OBSERVATION_END,
            observation_window_end=OBSERVATION_START,
        )


def test_create_agreement_rejects_baseline_overlapping_observation(direct_deploy):
    lacuna = direct_deploy("contracts/lacuna.py")
    with pytest.raises(Exception, match="baseline window must finish before"):
        create_agreement(
            lacuna,
            baseline_window_start=BASELINE_START,
            baseline_window_end=OBSERVATION_START + 1,
        )


def test_create_agreement_rejects_empty_title(direct_deploy):
    lacuna = direct_deploy("contracts/lacuna.py")
    with pytest.raises(Exception, match="title"):
        create_agreement(lacuna, title="")


def test_create_agreement_rejects_oversized_title(direct_deploy):
    lacuna = direct_deploy("contracts/lacuna.py")
    with pytest.raises(Exception, match="title"):
        create_agreement(lacuna, title="x" * 201)


def test_create_agreement_rejects_empty_obligation(direct_deploy):
    lacuna = direct_deploy("contracts/lacuna.py")
    with pytest.raises(Exception, match="obligation"):
        create_agreement(lacuna, obligation="")


def test_create_agreement_rejects_negative_escrow(direct_deploy):
    lacuna = direct_deploy("contracts/lacuna.py")
    with pytest.raises(Exception, match="escrow_amount"):
        create_agreement(lacuna, escrow_amount=-1)


def test_create_agreement_rejects_escrow_over_bound(direct_deploy):
    lacuna = direct_deploy("contracts/lacuna.py")
    with pytest.raises(Exception, match="escrow_amount"):
        create_agreement(lacuna, escrow_amount=(1 << 128))


def test_create_agreement_initial_status_is_draft(direct_deploy):
    lacuna = direct_deploy("contracts/lacuna.py")
    create_agreement(lacuna)
    record = json.loads(lacuna.get_agreement("AGR-1"))
    assert record["status"] == "DRAFT"


# =========================================================
# BaselineConstitution
# =========================================================


def test_create_baseline_constitution(direct_deploy):
    lacuna = direct_deploy("contracts/lacuna.py")
    constitution_id = make_constitution(lacuna)

    assert lacuna.constitution_count == 1
    record = json.loads(lacuna.get_baseline_constitution(constitution_id))
    assert record["name"] == "Community Health v1"
    assert record["version"] == 1
    assert record["status"] == "ACTIVE"
    assert record["primary_metric"] == "monthly_churn_bps"
    assert record["supporting_metric_schema"] == ["disputes", "escalations"]
    assert record["guardrail_metric_schema"] == ["contributor_retention", "member_activity"]
    assert record["minimum_evidence_categories"] == ["PUBLIC_ANALYTICS", "COMMUNITY_ACTIVITY"]
    assert record["minimum_independent_sources"] == 2
    assert record["falsification_rules"] == ["PRE_TREND_CHECK", "GUARDRAIL_CHECK"]


def test_constitution_versioning_supersedes_previous(direct_deploy):
    lacuna = direct_deploy("contracts/lacuna.py")
    v1_id = make_constitution(lacuna, name="Community Health")
    v2_id = make_constitution(lacuna, name="Community Health")

    v1 = json.loads(lacuna.get_baseline_constitution(v1_id))
    v2 = json.loads(lacuna.get_baseline_constitution(v2_id))

    assert v1["status"] == "INACTIVE"
    assert v2["status"] == "ACTIVE"
    assert v1["version"] == 1
    assert v2["version"] == 2
    assert lacuna.constitution_count == 2


def test_constitution_historical_versions_remain_queryable(direct_deploy):
    lacuna = direct_deploy("contracts/lacuna.py")
    v1_id = make_constitution(lacuna, name="Community Health")
    v2_id = make_constitution(lacuna, name="Community Health")

    versions = json.loads(lacuna.get_constitution_versions("Community Health"))
    assert versions == [v1_id, v2_id]

    # both versions still individually readable, unmutated apart from status
    v1 = json.loads(lacuna.get_baseline_constitution(v1_id))
    assert v1["name"] == "Community Health"
    assert v1["primary_metric"] == "monthly_churn_bps"


def test_list_constitutions_returns_all_versions(direct_deploy):
    lacuna = direct_deploy("contracts/lacuna.py")
    make_constitution(lacuna, name="A")
    make_constitution(lacuna, name="A")
    make_constitution(lacuna, name="B")

    listed = json.loads(lacuna.list_constitutions())
    assert len(listed) == 3


def test_create_constitution_rejects_empty_name(direct_deploy):
    lacuna = direct_deploy("contracts/lacuna.py")
    with pytest.raises(Exception, match="name"):
        make_constitution(lacuna, name="")


def test_create_constitution_rejects_unknown_evidence_category(direct_deploy):
    lacuna = direct_deploy("contracts/lacuna.py")
    with pytest.raises(Exception, match="minimum_evidence_categories"):
        lacuna.create_baseline_constitution(
            "Bad Constitution",
            "metric",
            [],
            [],
            "method",
            ["NOT_A_REAL_CATEGORY"],
            2,
            "policy",
            ["rule"],
            ["PRE_TREND_CHECK"],
        )


def test_create_constitution_rejects_unknown_falsification_check(direct_deploy):
    lacuna = direct_deploy("contracts/lacuna.py")
    with pytest.raises(Exception, match="falsification_rules"):
        lacuna.create_baseline_constitution(
            "Bad Constitution",
            "metric",
            [],
            [],
            "method",
            ["PUBLIC_ANALYTICS"],
            2,
            "policy",
            ["rule"],
            ["NOT_A_REAL_CHECK"],
        )


def test_create_constitution_rejects_zero_minimum_independent_sources(direct_deploy):
    lacuna = direct_deploy("contracts/lacuna.py")
    with pytest.raises(Exception, match="minimum_independent_sources"):
        lacuna.create_baseline_constitution(
            "Bad Constitution",
            "metric",
            [],
            [],
            "method",
            ["PUBLIC_ANALYTICS"],
            0,
            "policy",
            ["rule"],
            ["PRE_TREND_CHECK"],
        )


def test_create_constitution_rejects_empty_attribution_rules(direct_deploy):
    lacuna = direct_deploy("contracts/lacuna.py")
    with pytest.raises(Exception, match="attribution_rules"):
        lacuna.create_baseline_constitution(
            "Bad Constitution",
            "metric",
            [],
            [],
            "method",
            ["PUBLIC_ANALYTICS"],
            2,
            "policy",
            [],
            ["PRE_TREND_CHECK"],
        )


def test_get_baseline_constitution_missing_raises(direct_deploy):
    lacuna = direct_deploy("contracts/lacuna.py")
    with pytest.raises(Exception, match="not found"):
        lacuna.get_baseline_constitution("does-not-exist")


# =========================================================
# SettlementPolicy
# =========================================================


def test_create_settlement_policy(direct_deploy):
    lacuna = direct_deploy("contracts/lacuna.py")
    policy_id = make_policy(lacuna)

    assert lacuna.settlement_policy_count == 1
    record = json.loads(lacuna.get_settlement_policy(policy_id))
    assert record["name"] == "Standard Settlement v1"
    assert record["version"] == 1
    assert record["status"] == "ACTIVE"
    assert record["minimum_performance_bps"] == 2000
    assert record["full_payment_threshold_bps"] == 6000
    assert record["bonus_threshold_bps"] == 8000
    assert record["bonus_cap_bps"] == 1500
    assert record["max_unresolved_confounder_bps"] == 3000
    assert record["guardrail_failure_cap_bps"] == 4000


def test_settlement_policy_versioning_supersedes_previous(direct_deploy):
    lacuna = direct_deploy("contracts/lacuna.py")
    v1_id = make_policy(lacuna, name="Standard")
    v2_id = make_policy(lacuna, name="Standard")

    v1 = json.loads(lacuna.get_settlement_policy(v1_id))
    v2 = json.loads(lacuna.get_settlement_policy(v2_id))

    assert v1["status"] == "INACTIVE"
    assert v2["status"] == "ACTIVE"
    assert v1["version"] == 1
    assert v2["version"] == 2
    assert lacuna.settlement_policy_count == 2


def test_settlement_policy_historical_versions_remain_queryable(direct_deploy):
    lacuna = direct_deploy("contracts/lacuna.py")
    v1_id = make_policy(lacuna, name="Standard")
    v2_id = make_policy(lacuna, name="Standard")

    versions = json.loads(lacuna.get_settlement_policy_versions("Standard"))
    assert versions == [v1_id, v2_id]


def test_list_settlement_policies_returns_all_versions(direct_deploy):
    lacuna = direct_deploy("contracts/lacuna.py")
    make_policy(lacuna, name="A")
    make_policy(lacuna, name="A")
    make_policy(lacuna, name="B")

    listed = json.loads(lacuna.list_settlement_policies())
    assert len(listed) == 3


def test_create_settlement_policy_rejects_bps_out_of_range(direct_deploy):
    lacuna = direct_deploy("contracts/lacuna.py")
    with pytest.raises(Exception, match="minimum_performance_bps"):
        lacuna.create_settlement_policy("Bad Policy", 10001, 6000, 8000, 1500, 3000, 4000)


def test_create_settlement_policy_rejects_negative_bps(direct_deploy):
    lacuna = direct_deploy("contracts/lacuna.py")
    with pytest.raises(Exception, match="bonus_cap_bps"):
        lacuna.create_settlement_policy("Bad Policy", 2000, 6000, 8000, -1, 3000, 4000)


def test_create_settlement_policy_rejects_invalid_threshold_ordering_min_vs_full(direct_deploy):
    lacuna = direct_deploy("contracts/lacuna.py")
    with pytest.raises(Exception, match="minimum_performance_bps must be <= full_payment_threshold_bps"):
        lacuna.create_settlement_policy("Bad Policy", 7000, 6000, 8000, 1500, 3000, 4000)


def test_create_settlement_policy_rejects_invalid_threshold_ordering_full_vs_bonus(direct_deploy):
    lacuna = direct_deploy("contracts/lacuna.py")
    with pytest.raises(Exception, match="full_payment_threshold_bps must be <= bonus_threshold_bps"):
        lacuna.create_settlement_policy("Bad Policy", 2000, 9000, 8000, 1500, 3000, 4000)


def test_get_settlement_policy_missing_raises(direct_deploy):
    lacuna = direct_deploy("contracts/lacuna.py")
    with pytest.raises(Exception, match="not found"):
        lacuna.get_settlement_policy("does-not-exist")


# =========================================================
# BaselineEvidence
# =========================================================


def _hash_of(seed: str) -> str:
    return hashlib.sha256(seed.encode()).hexdigest()


def setup_agreement(lacuna, direct_vm, direct_alice, direct_bob, agreement_id="AGR-1", escrow_amount=10_000):
    """Deploys as default sender, wires client=alice, contractor=bob."""
    client = as_hex(direct_alice)
    contractor = as_hex(direct_bob)
    agreement_id, constitution_id, policy_id = create_agreement(
        lacuna, agreement_id=agreement_id, client=client, contractor=contractor,
        escrow_amount=escrow_amount
    )
    return agreement_id, constitution_id, policy_id, client, contractor


def submit_evidence(
    lacuna,
    agreement_id="AGR-1",
    evidence_id="EV-1",
    source_type="PUBLIC_ANALYTICS",
    source_url="https://analytics.example.com/report",
    content_hash=None,
    summary="Historical churn dashboard export for the baseline window.",
    metric_ref="monthly_churn_bps",
    period_start=1_700_100_000,
    period_end=1_700_150_000,
):
    if content_hash is None:
        content_hash = _hash_of(evidence_id + source_url)
    return lacuna.submit_baseline_evidence(
        evidence_id,
        agreement_id,
        source_type,
        source_url,
        content_hash,
        summary,
        metric_ref,
        period_start,
        period_end,
    )


def test_submit_baseline_evidence_valid(direct_deploy, direct_vm, direct_alice, direct_bob):
    lacuna = direct_deploy("contracts/lacuna.py")
    agreement_id, *_ , client, _contractor = setup_agreement(lacuna, direct_vm, direct_alice, direct_bob)

    direct_vm.sender = direct_alice
    evidence_id = submit_evidence(lacuna, agreement_id=agreement_id)

    assert evidence_id == "EV-1"
    assert lacuna.baseline_evidence_count == 1

    record = json.loads(lacuna.get_baseline_evidence("EV-1"))
    assert record["evidence_id"] == "EV-1"
    assert record["agreement_id"] == agreement_id
    assert record["submitter"].lower() == client.lower()
    assert record["source_type"] == "PUBLIC_ANALYTICS"
    assert record["source_url"] == "https://analytics.example.com/report"
    assert record["source_host"] == "analytics.example.com"
    assert record["metric_ref"] == "monthly_churn_bps"
    assert record["status"] == "SUBMITTED"

    listed = json.loads(lacuna.list_baseline_evidence(agreement_id))
    assert len(listed) == 1
    assert listed[0]["evidence_id"] == "EV-1"

    # first submission lazily advances the agreement out of DRAFT
    agreement = json.loads(lacuna.get_agreement(agreement_id))
    assert agreement["status"] == "BASELINE_OPEN"


def test_submit_baseline_evidence_by_contractor_also_allowed(direct_deploy, direct_vm, direct_alice, direct_bob):
    lacuna = direct_deploy("contracts/lacuna.py")
    agreement_id, *_ = setup_agreement(lacuna, direct_vm, direct_alice, direct_bob)

    direct_vm.sender = direct_bob
    submit_evidence(lacuna, agreement_id=agreement_id)
    assert lacuna.baseline_evidence_count == 1


def test_submit_baseline_evidence_rejects_unauthorized_submitter(
    direct_deploy, direct_vm, direct_alice, direct_bob, direct_charlie
):
    lacuna = direct_deploy("contracts/lacuna.py")
    agreement_id, *_ = setup_agreement(lacuna, direct_vm, direct_alice, direct_bob)

    direct_vm.sender = direct_charlie
    with pytest.raises(Exception, match="client or contractor"):
        submit_evidence(lacuna, agreement_id=agreement_id)


def test_submit_baseline_evidence_rejects_unknown_agreement(direct_deploy, direct_vm, direct_alice):
    lacuna = direct_deploy("contracts/lacuna.py")
    direct_vm.sender = direct_alice
    with pytest.raises(Exception, match="Agreement not found"):
        submit_evidence(lacuna, agreement_id="does-not-exist")


def test_submit_baseline_evidence_rejects_wrong_agreement_status(direct_deploy, direct_vm, direct_alice, direct_bob):
    lacuna = direct_deploy("contracts/lacuna.py")
    agreement_id, *_ = setup_agreement(lacuna, direct_vm, direct_alice, direct_bob)

    direct_vm.sender = direct_alice
    submit_evidence(
        lacuna,
        agreement_id=agreement_id,
        evidence_id="EV-1",
        source_type="PUBLIC_ANALYTICS",
        source_url="https://analytics.example.com/a",
    )
    submit_evidence(
        lacuna,
        agreement_id=agreement_id,
        evidence_id="EV-2",
        source_type="COMMUNITY_ACTIVITY",
        source_url="https://forum.example.org/b",
        period_start=1_700_200_000,
        period_end=1_700_250_000,
    )
    direct_vm.mock_web("analytics.example.com/a", {"status": 200, "body": "Stable historical analytics."})
    direct_vm.mock_web("forum.example.org/b", {"status": 200, "body": "Stable historical community activity."})
    lacuna.freeze_baseline_evidence(agreement_id)

    with pytest.raises(Exception, match="DRAFT or BASELINE_OPEN"):
        submit_evidence(lacuna, agreement_id=agreement_id, evidence_id="EV-3")


def test_submit_baseline_evidence_rejects_invalid_source_type(direct_deploy, direct_vm, direct_alice, direct_bob):
    lacuna = direct_deploy("contracts/lacuna.py")
    agreement_id, *_ = setup_agreement(lacuna, direct_vm, direct_alice, direct_bob)
    direct_vm.sender = direct_alice
    with pytest.raises(Exception, match="source_type"):
        submit_evidence(lacuna, agreement_id=agreement_id, source_type="NOT_A_REAL_CATEGORY")


def test_submit_baseline_evidence_rejects_invalid_url(direct_deploy, direct_vm, direct_alice, direct_bob):
    lacuna = direct_deploy("contracts/lacuna.py")
    agreement_id, *_ = setup_agreement(lacuna, direct_vm, direct_alice, direct_bob)
    direct_vm.sender = direct_alice
    with pytest.raises(Exception, match="source_url"):
        submit_evidence(lacuna, agreement_id=agreement_id, source_url="not-a-url")


def test_submit_baseline_evidence_rejects_invalid_content_hash(direct_deploy, direct_vm, direct_alice, direct_bob):
    lacuna = direct_deploy("contracts/lacuna.py")
    agreement_id, *_ = setup_agreement(lacuna, direct_vm, direct_alice, direct_bob)
    direct_vm.sender = direct_alice
    with pytest.raises(Exception, match="content_hash"):
        submit_evidence(lacuna, agreement_id=agreement_id, content_hash="not-a-hash")


def test_submit_baseline_evidence_rejects_empty_summary(direct_deploy, direct_vm, direct_alice, direct_bob):
    lacuna = direct_deploy("contracts/lacuna.py")
    agreement_id, *_ = setup_agreement(lacuna, direct_vm, direct_alice, direct_bob)
    direct_vm.sender = direct_alice
    with pytest.raises(Exception, match="summary"):
        submit_evidence(lacuna, agreement_id=agreement_id, summary="")


def test_submit_baseline_evidence_rejects_oversized_summary(direct_deploy, direct_vm, direct_alice, direct_bob):
    lacuna = direct_deploy("contracts/lacuna.py")
    agreement_id, *_ = setup_agreement(lacuna, direct_vm, direct_alice, direct_bob)
    direct_vm.sender = direct_alice
    with pytest.raises(Exception, match="summary"):
        submit_evidence(lacuna, agreement_id=agreement_id, summary="x" * 1001)


def test_submit_baseline_evidence_rejects_invalid_metric_ref(direct_deploy, direct_vm, direct_alice, direct_bob):
    lacuna = direct_deploy("contracts/lacuna.py")
    agreement_id, *_ = setup_agreement(lacuna, direct_vm, direct_alice, direct_bob)
    direct_vm.sender = direct_alice
    with pytest.raises(Exception, match="metric_ref"):
        submit_evidence(lacuna, agreement_id=agreement_id, metric_ref="not_in_constitution")


def test_submit_baseline_evidence_rejects_invalid_period(direct_deploy, direct_vm, direct_alice, direct_bob):
    lacuna = direct_deploy("contracts/lacuna.py")
    agreement_id, *_ = setup_agreement(lacuna, direct_vm, direct_alice, direct_bob)
    direct_vm.sender = direct_alice
    with pytest.raises(Exception, match="period_start must be before period_end"):
        submit_evidence(lacuna, agreement_id=agreement_id, period_start=1_700_150_000, period_end=1_700_100_000)


def test_submit_baseline_evidence_rejects_period_outside_baseline_window(
    direct_deploy, direct_vm, direct_alice, direct_bob
):
    lacuna = direct_deploy("contracts/lacuna.py")
    agreement_id, *_ = setup_agreement(lacuna, direct_vm, direct_alice, direct_bob)
    direct_vm.sender = direct_alice
    with pytest.raises(Exception, match="baseline window"):
        submit_evidence(
            lacuna,
            agreement_id=agreement_id,
            period_start=OBSERVATION_START,
            period_end=OBSERVATION_START + 1000,
        )


def test_submit_baseline_evidence_rejects_duplicate_evidence_id(direct_deploy, direct_vm, direct_alice, direct_bob):
    lacuna = direct_deploy("contracts/lacuna.py")
    agreement_id, *_ = setup_agreement(lacuna, direct_vm, direct_alice, direct_bob)
    direct_vm.sender = direct_alice
    submit_evidence(lacuna, agreement_id=agreement_id, evidence_id="EV-1")

    with pytest.raises(Exception, match="already exists"):
        submit_evidence(
            lacuna,
            agreement_id=agreement_id,
            evidence_id="EV-1",
            source_url="https://analytics.example.com/other",
        )


def test_submit_baseline_evidence_rejects_duplicate_content_hash(direct_deploy, direct_vm, direct_alice, direct_bob):
    lacuna = direct_deploy("contracts/lacuna.py")
    agreement_id, *_ = setup_agreement(lacuna, direct_vm, direct_alice, direct_bob)
    direct_vm.sender = direct_alice
    shared_hash = _hash_of("shared-content")
    submit_evidence(lacuna, agreement_id=agreement_id, evidence_id="EV-1", content_hash=shared_hash)

    with pytest.raises(Exception, match="Duplicate evidence"):
        submit_evidence(
            lacuna,
            agreement_id=agreement_id,
            evidence_id="EV-2",
            source_url="https://analytics.example.com/other",
            content_hash=shared_hash,
        )


def test_submit_baseline_evidence_cap_enforced(direct_deploy, direct_vm, direct_alice, direct_bob):
    lacuna = direct_deploy("contracts/lacuna.py")
    agreement_id, *_ = setup_agreement(lacuna, direct_vm, direct_alice, direct_bob)
    direct_vm.sender = direct_alice

    for i in range(48):
        submit_evidence(
            lacuna,
            agreement_id=agreement_id,
            evidence_id=f"EV-{i}",
            source_url=f"https://analytics.example.com/report-{i}",
            period_start=1_700_100_000 + i,
            period_end=1_700_100_001 + i,
        )

    assert lacuna.baseline_evidence_count == 48

    with pytest.raises(Exception, match="cap reached"):
        submit_evidence(
            lacuna,
            agreement_id=agreement_id,
            evidence_id="EV-overflow",
            source_url="https://analytics.example.com/report-overflow",
            period_start=1_700_100_100,
            period_end=1_700_100_101,
        )


def _submit_two_valid_categories(lacuna, agreement_id):
    submit_evidence(
        lacuna,
        agreement_id=agreement_id,
        evidence_id="EV-1",
        source_type="PUBLIC_ANALYTICS",
        source_url="https://analytics.example.com/report",
        period_start=1_700_100_000,
        period_end=1_700_150_000,
    )
    submit_evidence(
        lacuna,
        agreement_id=agreement_id,
        evidence_id="EV-2",
        source_type="COMMUNITY_ACTIVITY",
        source_url="https://forum.example.org/thread",
        period_start=1_700_200_000,
        period_end=1_700_250_000,
    )


def _mock_baseline_snapshots(direct_vm):
    direct_vm.mock_web("analytics.example.com/report", {"status": 200, "body": "Churn trended down steadily."})
    direct_vm.mock_web("forum.example.org/thread", {"status": 200, "body": "Community sentiment stable."})


def _mock_outcome_snapshots(direct_vm):
    direct_vm.mock_web("analytics.example.com/churn", {"status": 200, "body": "Churn dropped sharply after the change."})
    direct_vm.mock_web("community.example.org/retention", {"status": 200, "body": "Retention improved steadily."})
    direct_vm.mock_web("community.example.org/activity", {"status": 200, "body": "Activity stayed healthy."})


def test_freeze_baseline_evidence_succeeds(direct_deploy, direct_vm, direct_alice, direct_bob):
    lacuna = direct_deploy("contracts/lacuna.py")
    agreement_id, *_ = setup_agreement(lacuna, direct_vm, direct_alice, direct_bob)
    direct_vm.sender = direct_alice
    _submit_two_valid_categories(lacuna, agreement_id)
    _mock_baseline_snapshots(direct_vm)

    result = lacuna.freeze_baseline_evidence(agreement_id)
    assert result == agreement_id

    agreement = json.loads(lacuna.get_agreement(agreement_id))
    assert agreement["status"] == "BASELINE_FROZEN"

    listed = json.loads(lacuna.list_baseline_evidence(agreement_id))
    assert len(listed) == 2
    assert all(item["status"] == "FROZEN" for item in listed)
    assert listed[0]["submitted_content_hash"] == _hash_of("EV-1https://analytics.example.com/report")
    assert listed[0]["content_hash"] == listed[0]["frozen_content_hash"]
    assert listed[0]["content_hash"] == _hash_of(listed[0]["frozen_content"])


def test_freeze_baseline_evidence_rejects_unrelated_wallet(
    direct_deploy, direct_vm, direct_alice, direct_bob, direct_charlie,
):
    lacuna = direct_deploy("contracts/lacuna.py")
    agreement_id, *_ = setup_agreement(lacuna, direct_vm, direct_alice, direct_bob)
    direct_vm.sender = direct_alice
    _submit_two_valid_categories(lacuna, agreement_id)
    direct_vm.sender = direct_charlie
    with pytest.raises(Exception, match="client or contractor"):
        lacuna.freeze_baseline_evidence(agreement_id)


def test_freeze_baseline_evidence_rejects_before_any_evidence(direct_deploy, direct_vm, direct_alice, direct_bob):
    lacuna = direct_deploy("contracts/lacuna.py")
    agreement_id, *_ = setup_agreement(lacuna, direct_vm, direct_alice, direct_bob)
    direct_vm.sender = direct_alice

    with pytest.raises(Exception, match="BASELINE_OPEN"):
        lacuna.freeze_baseline_evidence(agreement_id)


def test_freeze_baseline_evidence_insufficient_evidence(direct_deploy, direct_vm, direct_alice, direct_bob):
    lacuna = direct_deploy("contracts/lacuna.py")
    agreement_id, *_ = setup_agreement(lacuna, direct_vm, direct_alice, direct_bob)
    direct_vm.sender = direct_alice
    submit_evidence(lacuna, agreement_id=agreement_id, evidence_id="EV-1")

    with pytest.raises(Exception, match="Insufficient baseline evidence"):
        lacuna.freeze_baseline_evidence(agreement_id)


def test_freeze_baseline_evidence_insufficient_evidence_categories(
    direct_deploy, direct_vm, direct_alice, direct_bob
):
    lacuna = direct_deploy("contracts/lacuna.py")
    agreement_id, *_ = setup_agreement(lacuna, direct_vm, direct_alice, direct_bob)
    direct_vm.sender = direct_alice
    submit_evidence(
        lacuna,
        agreement_id=agreement_id,
        evidence_id="EV-1",
        source_type="PUBLIC_ANALYTICS",
        source_url="https://analytics.example.com/a",
        period_start=1_700_100_000,
        period_end=1_700_150_000,
    )
    submit_evidence(
        lacuna,
        agreement_id=agreement_id,
        evidence_id="EV-2",
        source_type="PUBLIC_ANALYTICS",
        source_url="https://analytics.example.org/b",
        period_start=1_700_200_000,
        period_end=1_700_250_000,
    )

    with pytest.raises(Exception, match="Insufficient evidence categories"):
        lacuna.freeze_baseline_evidence(agreement_id)


def test_freeze_baseline_evidence_insufficient_independent_sources(
    direct_deploy, direct_vm, direct_alice, direct_bob
):
    lacuna = direct_deploy("contracts/lacuna.py")
    agreement_id, *_ = setup_agreement(lacuna, direct_vm, direct_alice, direct_bob)
    direct_vm.sender = direct_alice
    submit_evidence(
        lacuna,
        agreement_id=agreement_id,
        evidence_id="EV-1",
        source_type="PUBLIC_ANALYTICS",
        source_url="https://example.com/analytics-report",
        period_start=1_700_100_000,
        period_end=1_700_150_000,
    )
    submit_evidence(
        lacuna,
        agreement_id=agreement_id,
        evidence_id="EV-2",
        source_type="COMMUNITY_ACTIVITY",
        source_url="https://example.com/community-thread",
        period_start=1_700_200_000,
        period_end=1_700_250_000,
    )

    with pytest.raises(Exception, match="Insufficient independent sources"):
        lacuna.freeze_baseline_evidence(agreement_id)


def test_no_evidence_can_be_added_after_freeze(direct_deploy, direct_vm, direct_alice, direct_bob):
    lacuna = direct_deploy("contracts/lacuna.py")
    agreement_id, *_ = setup_agreement(lacuna, direct_vm, direct_alice, direct_bob)
    direct_vm.sender = direct_alice
    _submit_two_valid_categories(lacuna, agreement_id)
    _mock_baseline_snapshots(direct_vm)
    lacuna.freeze_baseline_evidence(agreement_id)

    with pytest.raises(Exception, match="DRAFT or BASELINE_OPEN"):
        submit_evidence(lacuna, agreement_id=agreement_id, evidence_id="EV-3")


def test_frozen_evidence_remains_queryable_and_immutable(direct_deploy, direct_vm, direct_alice, direct_bob):
    lacuna = direct_deploy("contracts/lacuna.py")
    agreement_id, *_ = setup_agreement(lacuna, direct_vm, direct_alice, direct_bob)
    direct_vm.sender = direct_alice
    _submit_two_valid_categories(lacuna, agreement_id)
    _mock_baseline_snapshots(direct_vm)
    lacuna.freeze_baseline_evidence(agreement_id)

    record = json.loads(lacuna.get_baseline_evidence("EV-1"))
    assert record["status"] == "FROZEN"
    assert record["summary"] == "Historical churn dashboard export for the baseline window."
    assert record["metric_ref"] == "monthly_churn_bps"

    listed = json.loads(lacuna.list_baseline_evidence(agreement_id))
    assert {item["evidence_id"] for item in listed} == {"EV-1", "EV-2"}


def test_tampered_frozen_snapshot_cannot_enter_baseline_adjudication(
    direct_deploy, direct_vm, direct_alice, direct_bob,
):
    lacuna = direct_deploy("contracts/lacuna.py")
    agreement_id = _ready_for_baseline_evaluation(lacuna, direct_vm, direct_alice, direct_bob)
    record = json.loads(lacuna.baseline_evidence["EV-1"])
    record["frozen_content"] = "tampered after freeze"
    lacuna.baseline_evidence["EV-1"] = json.dumps(record)
    direct_vm.mock_llm(r".*", _fenced(VALID_BASELINE_VERDICT))
    with pytest.raises(Exception, match="content hash mismatch"):
        lacuna.evaluate_baseline(agreement_id)


# =========================================================
# CounterfactualBaseline evaluation (Stage 4)
# =========================================================


def _fenced(obj) -> str:
    """Wrap JSON in markdown fences, as real LLM output typically is. Also
    keeps the mock response un-parseable as top-level JSON so gltest's
    direct-mode LLM mock does NOT auto-decode it into a dict -- the contract
    must receive a raw string and do its own fence-stripping/json.loads,
    exactly like production."""
    return "```json\n" + json.dumps(obj) + "\n```"


VALID_BASELINE_VERDICT = {
    "expected_value_bps": 3400,
    "expected_low_bps": 2900,
    "expected_high_bps": 4100,
    "confidence_bps": 8800,
    "method_valid": True,
    "reason_codes": ["HISTORICAL_TREND_SUPPORTED", "EXTERNAL_BENCHMARK_CONSISTENT"],
    "evidence_refs": ["EV-1", "EV-2"],
    "summary": "Historical trend and an external benchmark support a stable expected churn range.",
}

INVALID_METHOD_VERDICT = {
    "expected_value_bps": 0,
    "expected_low_bps": 0,
    "expected_high_bps": 0,
    "confidence_bps": 1000,
    "method_valid": False,
    "reason_codes": ["BASELINE_EVIDENCE_INSUFFICIENT"],
    "evidence_refs": [],
    "summary": "Evidence is too thin and internally inconsistent to support a defensible baseline.",
}


def _ready_for_baseline_evaluation(lacuna, direct_vm, direct_alice, direct_bob, agreement_id="AGR-1", escrow_amount=10_000):
    """Agreement with two categories of frozen baseline evidence, evidence
    source URLs mocked. Ready for evaluate_baseline()."""
    agreement_id, *_ = setup_agreement(
        lacuna, direct_vm, direct_alice, direct_bob,
        agreement_id=agreement_id, escrow_amount=escrow_amount
    )
    direct_vm.sender = direct_alice
    _submit_two_valid_categories(lacuna, agreement_id)
    _mock_baseline_snapshots(direct_vm)
    lacuna.freeze_baseline_evidence(agreement_id)
    return agreement_id


def test_evaluate_baseline_valid_stores_expected_range(direct_deploy, direct_vm, direct_alice, direct_bob):
    lacuna = direct_deploy("contracts/lacuna.py")
    agreement_id = _ready_for_baseline_evaluation(lacuna, direct_vm, direct_alice, direct_bob)
    direct_vm.mock_llm(r".*", _fenced(VALID_BASELINE_VERDICT))

    result = json.loads(lacuna.evaluate_baseline(agreement_id))
    assert result["expected_value_bps"] == 3400
    assert result["expected_low_bps"] == 2900
    assert result["expected_high_bps"] == 4100
    assert result["confidence_bps"] == 8800
    assert result["status"] == "PROPOSED"

    agreement = json.loads(lacuna.get_agreement(agreement_id))
    assert agreement["status"] == "BASELINE_PROPOSED"
    assert agreement["baseline_id"] == result["baseline_id"]

    baseline = json.loads(lacuna.get_counterfactual_baseline(result["baseline_id"]))
    assert baseline["expected_value_bps"] == 3400
    assert baseline["status"] == "PROPOSED"


def test_evaluate_baseline_preserves_evidence_refs(direct_deploy, direct_vm, direct_alice, direct_bob):
    lacuna = direct_deploy("contracts/lacuna.py")
    agreement_id = _ready_for_baseline_evaluation(lacuna, direct_vm, direct_alice, direct_bob)
    direct_vm.mock_llm(r".*", _fenced(VALID_BASELINE_VERDICT))

    result = json.loads(lacuna.evaluate_baseline(agreement_id))
    assert result["evidence_refs"] == ["EV-1", "EV-2"]
    assert result["reason_codes"] == ["HISTORICAL_TREND_SUPPORTED", "EXTERNAL_BENCHMARK_CONSISTENT"]


def test_evaluate_baseline_rejects_malformed_json(direct_deploy, direct_vm, direct_alice, direct_bob):
    lacuna = direct_deploy("contracts/lacuna.py")
    agreement_id = _ready_for_baseline_evaluation(lacuna, direct_vm, direct_alice, direct_bob)
    direct_vm.mock_llm(r".*", "this is not json at all")

    with pytest.raises(Exception, match="not valid JSON"):
        lacuna.evaluate_baseline(agreement_id)


def test_evaluate_baseline_rejects_non_object_json(direct_deploy, direct_vm, direct_alice, direct_bob):
    lacuna = direct_deploy("contracts/lacuna.py")
    agreement_id = _ready_for_baseline_evaluation(lacuna, direct_vm, direct_alice, direct_bob)
    direct_vm.mock_llm(r".*", _fenced([1, 2, 3]))

    with pytest.raises(Exception, match="expected a JSON object"):
        lacuna.evaluate_baseline(agreement_id)


def test_evaluate_baseline_rejects_missing_field(direct_deploy, direct_vm, direct_alice, direct_bob):
    lacuna = direct_deploy("contracts/lacuna.py")
    agreement_id = _ready_for_baseline_evaluation(lacuna, direct_vm, direct_alice, direct_bob)
    bad = dict(VALID_BASELINE_VERDICT)
    del bad["summary"]
    direct_vm.mock_llm(r".*", _fenced(bad))

    with pytest.raises(Exception, match="missing field 'summary'"):
        lacuna.evaluate_baseline(agreement_id)


def test_evaluate_baseline_rejects_extra_unknown_fields(direct_deploy, direct_vm, direct_alice, direct_bob):
    lacuna = direct_deploy("contracts/lacuna.py")
    agreement_id = _ready_for_baseline_evaluation(lacuna, direct_vm, direct_alice, direct_bob)
    extra = dict(VALID_BASELINE_VERDICT, unexpected_field="ignored", another_bonus_key=123)
    direct_vm.mock_llm(r".*", _fenced(extra))

    with pytest.raises(Exception, match="unsupported field"):
        lacuna.evaluate_baseline(agreement_id)


def test_evaluate_baseline_rejects_wrong_field_type(direct_deploy, direct_vm, direct_alice, direct_bob):
    lacuna = direct_deploy("contracts/lacuna.py")
    agreement_id = _ready_for_baseline_evaluation(lacuna, direct_vm, direct_alice, direct_bob)
    bad = dict(VALID_BASELINE_VERDICT, confidence_bps="high")
    direct_vm.mock_llm(r".*", _fenced(bad))

    with pytest.raises(Exception, match="confidence_bps must be an integer"):
        lacuna.evaluate_baseline(agreement_id)


def test_evaluate_baseline_rejects_bps_below_zero(direct_deploy, direct_vm, direct_alice, direct_bob):
    lacuna = direct_deploy("contracts/lacuna.py")
    agreement_id = _ready_for_baseline_evaluation(lacuna, direct_vm, direct_alice, direct_bob)
    bad = dict(VALID_BASELINE_VERDICT, confidence_bps=-1)
    direct_vm.mock_llm(r".*", _fenced(bad))

    with pytest.raises(Exception, match="confidence_bps must be between 0 and 10000"):
        lacuna.evaluate_baseline(agreement_id)


def test_evaluate_baseline_rejects_bps_above_10000(direct_deploy, direct_vm, direct_alice, direct_bob):
    lacuna = direct_deploy("contracts/lacuna.py")
    agreement_id = _ready_for_baseline_evaluation(lacuna, direct_vm, direct_alice, direct_bob)
    bad = dict(VALID_BASELINE_VERDICT, expected_high_bps=10001)
    direct_vm.mock_llm(r".*", _fenced(bad))

    with pytest.raises(Exception, match="expected_high_bps must be between 0 and 10000"):
        lacuna.evaluate_baseline(agreement_id)


def test_evaluate_baseline_rejects_low_greater_than_expected(direct_deploy, direct_vm, direct_alice, direct_bob):
    lacuna = direct_deploy("contracts/lacuna.py")
    agreement_id = _ready_for_baseline_evaluation(lacuna, direct_vm, direct_alice, direct_bob)
    bad = dict(VALID_BASELINE_VERDICT, expected_low_bps=3500)
    direct_vm.mock_llm(r".*", _fenced(bad))

    with pytest.raises(Exception, match="expected_low_bps must be <= expected_value_bps <= expected_high_bps"):
        lacuna.evaluate_baseline(agreement_id)


def test_evaluate_baseline_rejects_expected_greater_than_high(direct_deploy, direct_vm, direct_alice, direct_bob):
    lacuna = direct_deploy("contracts/lacuna.py")
    agreement_id = _ready_for_baseline_evaluation(lacuna, direct_vm, direct_alice, direct_bob)
    bad = dict(VALID_BASELINE_VERDICT, expected_value_bps=4200)
    direct_vm.mock_llm(r".*", _fenced(bad))

    with pytest.raises(Exception, match="expected_low_bps must be <= expected_value_bps <= expected_high_bps"):
        lacuna.evaluate_baseline(agreement_id)


def test_evaluate_baseline_rejects_unknown_reason_code(direct_deploy, direct_vm, direct_alice, direct_bob):
    lacuna = direct_deploy("contracts/lacuna.py")
    agreement_id = _ready_for_baseline_evaluation(lacuna, direct_vm, direct_alice, direct_bob)
    bad = dict(VALID_BASELINE_VERDICT, reason_codes=["NOT_A_REAL_CODE"])
    direct_vm.mock_llm(r".*", _fenced(bad))

    with pytest.raises(Exception, match="Unknown reason code: NOT_A_REAL_CODE"):
        lacuna.evaluate_baseline(agreement_id)


def test_evaluate_baseline_rejects_nonexistent_evidence_ref(direct_deploy, direct_vm, direct_alice, direct_bob):
    lacuna = direct_deploy("contracts/lacuna.py")
    agreement_id = _ready_for_baseline_evaluation(lacuna, direct_vm, direct_alice, direct_bob)
    bad = dict(VALID_BASELINE_VERDICT, evidence_refs=["EV-does-not-exist"])
    direct_vm.mock_llm(r".*", _fenced(bad))

    with pytest.raises(Exception, match="evidence_refs references evidence outside the frozen baseline evidence set"):
        lacuna.evaluate_baseline(agreement_id)


def test_evaluate_baseline_rejects_duplicate_evidence_ref(direct_deploy, direct_vm, direct_alice, direct_bob):
    lacuna = direct_deploy("contracts/lacuna.py")
    agreement_id = _ready_for_baseline_evaluation(lacuna, direct_vm, direct_alice, direct_bob)
    bad = dict(VALID_BASELINE_VERDICT, evidence_refs=["EV-1", "EV-1"])
    direct_vm.mock_llm(r".*", _fenced(bad))

    with pytest.raises(Exception, match="evidence_refs must not contain duplicate references"):
        lacuna.evaluate_baseline(agreement_id)


def test_evaluate_baseline_rejects_empty_summary(direct_deploy, direct_vm, direct_alice, direct_bob):
    lacuna = direct_deploy("contracts/lacuna.py")
    agreement_id = _ready_for_baseline_evaluation(lacuna, direct_vm, direct_alice, direct_bob)
    bad = dict(VALID_BASELINE_VERDICT, summary="")
    direct_vm.mock_llm(r".*", _fenced(bad))

    with pytest.raises(Exception, match="summary must be 1-"):
        lacuna.evaluate_baseline(agreement_id)


def test_evaluate_baseline_rejects_oversized_summary(direct_deploy, direct_vm, direct_alice, direct_bob):
    lacuna = direct_deploy("contracts/lacuna.py")
    agreement_id = _ready_for_baseline_evaluation(lacuna, direct_vm, direct_alice, direct_bob)
    bad = dict(VALID_BASELINE_VERDICT, summary="x" * 1001)
    direct_vm.mock_llm(r".*", _fenced(bad))

    with pytest.raises(Exception, match="summary must be 1-"):
        lacuna.evaluate_baseline(agreement_id)


def test_freeze_baseline_rejects_source_that_cannot_be_snapshotted(direct_deploy, direct_vm, direct_alice, direct_bob):
    lacuna = direct_deploy("contracts/lacuna.py")
    agreement_id, *_ = setup_agreement(lacuna, direct_vm, direct_alice, direct_bob)
    direct_vm.sender = direct_alice
    _submit_two_valid_categories(lacuna, agreement_id)
    # No mock_web registered: a source that cannot be consensus-snapshotted
    # cannot enter an immutable evidence package.
    with pytest.raises(Exception, match="Unable to capture"):
        lacuna.freeze_baseline_evidence(agreement_id)
    assert json.loads(lacuna.get_agreement(agreement_id))["status"] == "BASELINE_OPEN"


def test_evaluate_baseline_handles_contradictory_evidence(direct_deploy, direct_vm, direct_alice, direct_bob):
    lacuna = direct_deploy("contracts/lacuna.py")
    agreement_id = _ready_for_baseline_evaluation(lacuna, direct_vm, direct_alice, direct_bob)
    conflicted_verdict = dict(
        VALID_BASELINE_VERDICT,
        confidence_bps=4000,
        reason_codes=["BASELINE_SOURCE_CONFLICT"],
        summary="Sources disagree on the direction of the trend; confidence reduced accordingly.",
    )
    direct_vm.mock_llm(r".*", _fenced(conflicted_verdict))

    result = json.loads(lacuna.evaluate_baseline(agreement_id))
    assert result["reason_codes"] == ["BASELINE_SOURCE_CONFLICT"]
    assert result["confidence_bps"] == 4000


def test_evaluate_baseline_method_invalid_does_not_advance_agreement(
    direct_deploy, direct_vm, direct_alice, direct_bob
):
    lacuna = direct_deploy("contracts/lacuna.py")
    agreement_id = _ready_for_baseline_evaluation(lacuna, direct_vm, direct_alice, direct_bob)
    direct_vm.mock_llm(r".*", _fenced(INVALID_METHOD_VERDICT))

    result = json.loads(lacuna.evaluate_baseline(agreement_id))
    assert result["status"] == "VOID"

    agreement = json.loads(lacuna.get_agreement(agreement_id))
    assert agreement["status"] == "BASELINE_FROZEN"
    assert agreement["baseline_id"] == ""

    # the conclusion is preserved and independently queryable
    baseline = json.loads(lacuna.get_counterfactual_baseline(result["baseline_id"]))
    assert baseline["status"] == "VOID"
    assert baseline["reason_codes"] == ["BASELINE_EVIDENCE_INSUFFICIENT"]

    # frozen evidence was never touched
    evidence = json.loads(lacuna.list_baseline_evidence(agreement_id))
    assert all(item["status"] == "FROZEN" for item in evidence)


def test_evaluate_baseline_can_be_retried_after_invalid_methodology(
    direct_deploy, direct_vm, direct_alice, direct_bob
):
    lacuna = direct_deploy("contracts/lacuna.py")
    agreement_id = _ready_for_baseline_evaluation(lacuna, direct_vm, direct_alice, direct_bob)
    direct_vm.mock_llm(r".*", _fenced(INVALID_METHOD_VERDICT))
    lacuna.evaluate_baseline(agreement_id)

    direct_vm.clear_mocks()  # drop the stale VOID-verdict mock (first match wins)
    direct_vm.mock_web("analytics.example.com/report", {"status": 200, "body": "Churn trended down steadily."})
    direct_vm.mock_web("forum.example.org/thread", {"status": 200, "body": "Community sentiment stable."})
    direct_vm.mock_llm(r".*", _fenced(VALID_BASELINE_VERDICT))
    result = json.loads(lacuna.evaluate_baseline(agreement_id))
    assert result["status"] == "PROPOSED"

    agreement = json.loads(lacuna.get_agreement(agreement_id))
    assert agreement["status"] == "BASELINE_PROPOSED"

    history = json.loads(lacuna.list_baseline_evaluations(agreement_id))
    assert len(history) == 2
    assert history[0]["status"] == "VOID"
    assert history[1]["status"] == "PROPOSED"


def test_evaluate_baseline_cannot_run_before_baseline_frozen(direct_deploy, direct_vm, direct_alice, direct_bob):
    lacuna = direct_deploy("contracts/lacuna.py")
    agreement_id, *_ = setup_agreement(lacuna, direct_vm, direct_alice, direct_bob)
    direct_vm.sender = direct_alice
    direct_vm.mock_llm(r".*", _fenced(VALID_BASELINE_VERDICT))

    with pytest.raises(Exception, match="BASELINE_FROZEN"):
        lacuna.evaluate_baseline(agreement_id)


def test_repeated_evaluation_cannot_overwrite_valid_proposed_baseline(
    direct_deploy, direct_vm, direct_alice, direct_bob
):
    lacuna = direct_deploy("contracts/lacuna.py")
    agreement_id = _ready_for_baseline_evaluation(lacuna, direct_vm, direct_alice, direct_bob)
    direct_vm.mock_llm(r".*", _fenced(VALID_BASELINE_VERDICT))
    first = json.loads(lacuna.evaluate_baseline(agreement_id))

    direct_vm.mock_llm(r".*", _fenced(dict(VALID_BASELINE_VERDICT, expected_value_bps=9999, expected_low_bps=9998, expected_high_bps=10000)))
    with pytest.raises(Exception, match="BASELINE_FROZEN"):
        lacuna.evaluate_baseline(agreement_id)

    agreement = json.loads(lacuna.get_agreement(agreement_id))
    assert agreement["baseline_id"] == first["baseline_id"]
    unchanged = json.loads(lacuna.get_counterfactual_baseline(first["baseline_id"]))
    assert unchanged["expected_value_bps"] == 3400


def test_evaluate_baseline_requires_authorized_party(
    direct_deploy, direct_vm, direct_alice, direct_bob, direct_charlie
):
    lacuna = direct_deploy("contracts/lacuna.py")
    agreement_id = _ready_for_baseline_evaluation(lacuna, direct_vm, direct_alice, direct_bob)
    direct_vm.mock_llm(r".*", _fenced(VALID_BASELINE_VERDICT))
    direct_vm.sender = direct_charlie

    with pytest.raises(Exception, match="client or contractor"):
        lacuna.evaluate_baseline(agreement_id)


def test_evaluate_baseline_rejects_unknown_agreement(direct_deploy, direct_vm, direct_alice):
    lacuna = direct_deploy("contracts/lacuna.py")
    direct_vm.sender = direct_alice
    with pytest.raises(Exception, match="Agreement not found"):
        lacuna.evaluate_baseline("does-not-exist")


# =========================================================
# BaselineChallenge, acceptance, and permanent lock (Stage 5)
# =========================================================


UPHOLD_VERDICT = {
    "decision": "UPHOLD",
    "replacement_required": False,
    "expected_value_bps": 3400,
    "expected_low_bps": 2900,
    "expected_high_bps": 4100,
    "confidence_bps": 8800,
    "reason_codes": ["HISTORICAL_TREND_SUPPORTED"],
    "evidence_refs": ["EV-1"],
    "summary": "The original baseline is defensible; the challenge does not identify a material flaw.",
}

MODIFY_VERDICT = {
    "decision": "MODIFY",
    "replacement_required": True,
    "expected_value_bps": 3000,
    "expected_low_bps": 2500,
    "expected_high_bps": 3600,
    "confidence_bps": 7000,
    "reason_codes": ["COMPARABILITY_LOW"],
    "evidence_refs": ["EV-1", "EV-2"],
    "summary": "The original range ignored a comparability issue; the corrected range accounts for it.",
}

VOID_CHALLENGE_VERDICT = {
    "decision": "VOID",
    "replacement_required": False,
    "expected_value_bps": 0,
    "expected_low_bps": 0,
    "expected_high_bps": 0,
    "confidence_bps": 0,
    "reason_codes": ["BASELINE_EVIDENCE_INSUFFICIENT"],
    "evidence_refs": [],
    "summary": "No defensible baseline can be salvaged from the available evidence given the challenge.",
}


def _proposed_agreement(lacuna, direct_vm, direct_alice, direct_bob, agreement_id="AGR-1", escrow_amount=10_000):
    """Agreement with a valid PROPOSED baseline (EV-1/EV-2 evidence, web
    mocks registered). Ready for open_baseline_challenge()/accept_baseline()."""
    agreement_id = _ready_for_baseline_evaluation(
        lacuna, direct_vm, direct_alice, direct_bob,
        agreement_id=agreement_id, escrow_amount=escrow_amount
    )
    direct_vm.mock_llm(r".*", _fenced(VALID_BASELINE_VERDICT))
    result = json.loads(lacuna.evaluate_baseline(agreement_id))
    direct_vm.clear_mocks()  # drop the stage-4 verdict mock so challenge tests control their own
    direct_vm.mock_web("analytics.example.com/report", {"status": 200, "body": "Churn trended down steadily."})
    direct_vm.mock_web("forum.example.org/thread", {"status": 200, "body": "Community sentiment stable."})
    return agreement_id, result["baseline_id"]


def test_open_baseline_challenge_valid(direct_deploy, direct_vm, direct_alice, direct_bob):
    lacuna = direct_deploy("contracts/lacuna.py")
    agreement_id, baseline_id = _proposed_agreement(lacuna, direct_vm, direct_alice, direct_bob)

    direct_vm.sender = direct_bob
    challenge_id = lacuna.open_baseline_challenge(
        "CH-1", agreement_id, "COMPARABLE_PERIOD_IGNORED", "The comparison period ignores a known confound.", ["EV-1"]
    )
    assert challenge_id == "CH-1"

    record = json.loads(lacuna.get_baseline_challenge("CH-1"))
    assert record["baseline_id"] == baseline_id
    assert record["agreement_id"] == agreement_id
    assert record["reason_code"] == "COMPARABLE_PERIOD_IGNORED"
    assert record["status"] == "OPEN"
    assert record["evidence_refs"] == ["EV-1"]

    agreement = json.loads(lacuna.get_agreement(agreement_id))
    assert agreement["status"] == "BASELINE_CHALLENGED"

    # the proposed baseline itself remains queryable, unmutated apart from status
    baseline = json.loads(lacuna.get_counterfactual_baseline(baseline_id))
    assert baseline["status"] == "CHALLENGED"
    assert baseline["expected_value_bps"] == 3400

    listed = json.loads(lacuna.list_baseline_challenges(baseline_id))
    assert len(listed) == 1
    assert listed[0]["challenge_id"] == "CH-1"


def test_open_baseline_challenge_rejects_unauthorized_challenger(
    direct_deploy, direct_vm, direct_alice, direct_bob, direct_charlie
):
    lacuna = direct_deploy("contracts/lacuna.py")
    agreement_id, _ = _proposed_agreement(lacuna, direct_vm, direct_alice, direct_bob)

    direct_vm.sender = direct_charlie
    with pytest.raises(Exception, match="client or contractor"):
        lacuna.open_baseline_challenge("CH-1", agreement_id, "EVIDENCE_OMITTED", "Not my business but I object.", [])


def test_open_baseline_challenge_rejects_wrong_agreement_status(direct_deploy, direct_vm, direct_alice, direct_bob):
    lacuna = direct_deploy("contracts/lacuna.py")
    agreement_id = _ready_for_baseline_evaluation(lacuna, direct_vm, direct_alice, direct_bob)
    # not yet evaluated -> still BASELINE_FROZEN

    direct_vm.sender = direct_alice
    with pytest.raises(Exception, match="BASELINE_PROPOSED"):
        lacuna.open_baseline_challenge("CH-1", agreement_id, "EVIDENCE_OMITTED", "Too early to challenge.", [])


def test_open_baseline_challenge_rejects_invalid_ground(direct_deploy, direct_vm, direct_alice, direct_bob):
    lacuna = direct_deploy("contracts/lacuna.py")
    agreement_id, _ = _proposed_agreement(lacuna, direct_vm, direct_alice, direct_bob)

    direct_vm.sender = direct_alice
    with pytest.raises(Exception, match="reason_code"):
        lacuna.open_baseline_challenge("CH-1", agreement_id, "NOT_A_REAL_GROUND", "Statement.", [])


def test_open_baseline_challenge_rejects_invalid_evidence_ref(direct_deploy, direct_vm, direct_alice, direct_bob):
    lacuna = direct_deploy("contracts/lacuna.py")
    agreement_id, _ = _proposed_agreement(lacuna, direct_vm, direct_alice, direct_bob)

    direct_vm.sender = direct_alice
    with pytest.raises(Exception, match="evidence_refs references evidence outside"):
        lacuna.open_baseline_challenge("CH-1", agreement_id, "EVIDENCE_OMITTED", "Statement.", ["EV-does-not-exist"])


def test_open_baseline_challenge_rejects_duplicate_evidence_ref(direct_deploy, direct_vm, direct_alice, direct_bob):
    lacuna = direct_deploy("contracts/lacuna.py")
    agreement_id, _ = _proposed_agreement(lacuna, direct_vm, direct_alice, direct_bob)

    direct_vm.sender = direct_alice
    with pytest.raises(Exception, match="duplicate references"):
        lacuna.open_baseline_challenge("CH-1", agreement_id, "EVIDENCE_OMITTED", "Statement.", ["EV-1", "EV-1"])


def test_open_baseline_challenge_rejects_duplicate_unresolved_challenge(
    direct_deploy, direct_vm, direct_alice, direct_bob
):
    lacuna = direct_deploy("contracts/lacuna.py")
    agreement_id, _ = _proposed_agreement(lacuna, direct_vm, direct_alice, direct_bob)

    direct_vm.sender = direct_alice
    lacuna.open_baseline_challenge("CH-1", agreement_id, "EVIDENCE_OMITTED", "First challenge.", [])

    # A second challenge cannot be opened while the agreement/baseline is
    # already BASELINE_CHALLENGED -- the status guard alone blocks this,
    # which is exactly the intended enforcement of "no unresolved challenge
    # already exists".
    with pytest.raises(Exception, match="BASELINE_PROPOSED"):
        lacuna.open_baseline_challenge("CH-2", agreement_id, "EVIDENCE_OMITTED", "Second challenge.", [])


def test_evaluate_baseline_challenge_uphold(direct_deploy, direct_vm, direct_alice, direct_bob):
    lacuna = direct_deploy("contracts/lacuna.py")
    agreement_id, baseline_id = _proposed_agreement(lacuna, direct_vm, direct_alice, direct_bob)
    direct_vm.sender = direct_alice
    lacuna.open_baseline_challenge("CH-1", agreement_id, "EVIDENCE_OMITTED", "The evaluation ignored EV-2.", ["EV-2"])

    direct_vm.mock_llm(r".*", _fenced(UPHOLD_VERDICT))
    result = json.loads(lacuna.evaluate_baseline_challenge("CH-1"))
    assert result["status"] == "RESOLVED"
    assert result["resolution"] == "UPHOLD"
    assert result["replacement_baseline_id"] == ""

    agreement = json.loads(lacuna.get_agreement(agreement_id))
    assert agreement["status"] == "BASELINE_PROPOSED"
    assert agreement["baseline_id"] == baseline_id

    baseline = json.loads(lacuna.get_counterfactual_baseline(baseline_id))
    assert baseline["status"] == "PROPOSED"
    assert baseline["expected_value_bps"] == 3400  # unmutated


def test_evaluate_baseline_challenge_modify(direct_deploy, direct_vm, direct_alice, direct_bob):
    lacuna = direct_deploy("contracts/lacuna.py")
    agreement_id, original_id = _proposed_agreement(lacuna, direct_vm, direct_alice, direct_bob)
    direct_vm.sender = direct_alice
    lacuna.open_baseline_challenge("CH-1", agreement_id, "COMPARABLE_PERIOD_IGNORED", "Comparability issue.", ["EV-1", "EV-2"])

    direct_vm.mock_llm(r".*", _fenced(MODIFY_VERDICT))
    result = json.loads(lacuna.evaluate_baseline_challenge("CH-1"))
    assert result["resolution"] == "MODIFY"
    replacement_id = result["replacement_baseline_id"]
    assert replacement_id
    assert replacement_id != original_id

    agreement = json.loads(lacuna.get_agreement(agreement_id))
    assert agreement["status"] == "BASELINE_PROPOSED"
    assert agreement["baseline_id"] == replacement_id
    assert agreement["client_baseline_acceptance"] is False
    assert agreement["contractor_baseline_acceptance"] is False

    replacement = json.loads(lacuna.get_counterfactual_baseline(replacement_id))
    assert replacement["status"] == "PROPOSED"
    assert replacement["expected_value_bps"] == 3000

    # original baseline preserved, superseded, still queryable
    original = json.loads(lacuna.get_counterfactual_baseline(original_id))
    assert original["status"] == "VOID"
    assert original["expected_value_bps"] == 3400

    history = json.loads(lacuna.list_baseline_evaluations(agreement_id))
    assert {b["baseline_id"] for b in history} == {original_id, replacement_id}


def test_evaluate_baseline_challenge_void(direct_deploy, direct_vm, direct_alice, direct_bob):
    lacuna = direct_deploy("contracts/lacuna.py")
    agreement_id, baseline_id = _proposed_agreement(lacuna, direct_vm, direct_alice, direct_bob)
    direct_vm.sender = direct_alice
    lacuna.open_baseline_challenge("CH-1", agreement_id, "BASELINE_MISCONSTRUCTED", "No defensible method here.", [])

    direct_vm.mock_llm(r".*", _fenced(VOID_CHALLENGE_VERDICT))
    result = json.loads(lacuna.evaluate_baseline_challenge("CH-1"))
    assert result["resolution"] == "VOID"

    agreement = json.loads(lacuna.get_agreement(agreement_id))
    assert agreement["status"] == "BASELINE_FROZEN"
    assert agreement["baseline_id"] == ""

    baseline = json.loads(lacuna.get_counterfactual_baseline(baseline_id))
    assert baseline["status"] == "VOID"

    # frozen evidence never touched, and evaluate_baseline can run again
    evidence = json.loads(lacuna.list_baseline_evidence(agreement_id))
    assert all(item["status"] == "FROZEN" for item in evidence)

    direct_vm.clear_mocks()  # drop the stale VOID challenge-verdict mock (first match wins)
    direct_vm.mock_web("analytics.example.com/report", {"status": 200, "body": "Churn trended down steadily."})
    direct_vm.mock_web("forum.example.org/thread", {"status": 200, "body": "Community sentiment stable."})
    direct_vm.mock_llm(r".*", _fenced(VALID_BASELINE_VERDICT))
    retried = json.loads(lacuna.evaluate_baseline(agreement_id))
    assert retried["status"] == "PROPOSED"


def test_evaluate_baseline_challenge_rejects_malformed_json(direct_deploy, direct_vm, direct_alice, direct_bob):
    lacuna = direct_deploy("contracts/lacuna.py")
    agreement_id, _ = _proposed_agreement(lacuna, direct_vm, direct_alice, direct_bob)
    direct_vm.sender = direct_alice
    lacuna.open_baseline_challenge("CH-1", agreement_id, "EVIDENCE_OMITTED", "Statement.", [])

    direct_vm.mock_llm(r".*", "not json")
    with pytest.raises(Exception, match="not valid JSON"):
        lacuna.evaluate_baseline_challenge("CH-1")


def test_evaluate_baseline_challenge_rejects_invalid_bps(direct_deploy, direct_vm, direct_alice, direct_bob):
    lacuna = direct_deploy("contracts/lacuna.py")
    agreement_id, _ = _proposed_agreement(lacuna, direct_vm, direct_alice, direct_bob)
    direct_vm.sender = direct_alice
    lacuna.open_baseline_challenge("CH-1", agreement_id, "EVIDENCE_OMITTED", "Statement.", [])

    bad = dict(UPHOLD_VERDICT, confidence_bps=20000)
    direct_vm.mock_llm(r".*", _fenced(bad))
    with pytest.raises(Exception, match="confidence_bps must be between 0 and 10000"):
        lacuna.evaluate_baseline_challenge("CH-1")


def test_evaluate_baseline_challenge_rejects_invalid_replacement_range(
    direct_deploy, direct_vm, direct_alice, direct_bob
):
    lacuna = direct_deploy("contracts/lacuna.py")
    agreement_id, _ = _proposed_agreement(lacuna, direct_vm, direct_alice, direct_bob)
    direct_vm.sender = direct_alice
    lacuna.open_baseline_challenge("CH-1", agreement_id, "COMPARABLE_PERIOD_IGNORED", "Statement.", [])

    bad = dict(MODIFY_VERDICT, expected_low_bps=4000)  # low > expected
    direct_vm.mock_llm(r".*", _fenced(bad))
    with pytest.raises(Exception, match="expected_low_bps must be <= expected_value_bps <= expected_high_bps"):
        lacuna.evaluate_baseline_challenge("CH-1")


def test_evaluate_baseline_challenge_rejects_decision_replacement_mismatch(
    direct_deploy, direct_vm, direct_alice, direct_bob
):
    lacuna = direct_deploy("contracts/lacuna.py")
    agreement_id, _ = _proposed_agreement(lacuna, direct_vm, direct_alice, direct_bob)
    direct_vm.sender = direct_alice
    lacuna.open_baseline_challenge("CH-1", agreement_id, "EVIDENCE_OMITTED", "Statement.", [])

    bad = dict(UPHOLD_VERDICT, replacement_required=True)
    direct_vm.mock_llm(r".*", _fenced(bad))
    with pytest.raises(Exception, match="replacement_required must be true if and only if decision is MODIFY"):
        lacuna.evaluate_baseline_challenge("CH-1")


def test_evaluate_baseline_challenge_requires_open_status(direct_deploy, direct_vm, direct_alice, direct_bob):
    lacuna = direct_deploy("contracts/lacuna.py")
    agreement_id, _ = _proposed_agreement(lacuna, direct_vm, direct_alice, direct_bob)
    direct_vm.sender = direct_alice
    lacuna.open_baseline_challenge("CH-1", agreement_id, "EVIDENCE_OMITTED", "Statement.", [])
    direct_vm.mock_llm(r".*", _fenced(UPHOLD_VERDICT))
    lacuna.evaluate_baseline_challenge("CH-1")

    with pytest.raises(Exception, match="already been resolved"):
        lacuna.evaluate_baseline_challenge("CH-1")


def test_accept_baseline_valid_dual_party(direct_deploy, direct_vm, direct_alice, direct_bob):
    lacuna = direct_deploy("contracts/lacuna.py")
    agreement_id, baseline_id = _proposed_agreement(lacuna, direct_vm, direct_alice, direct_bob)

    direct_vm.sender = direct_alice
    result = json.loads(lacuna.accept_baseline(agreement_id))
    assert result["status"] == "BASELINE_PROPOSED"  # not final yet -- only one party accepted
    assert result["client_baseline_acceptance"] is True
    assert result["contractor_baseline_acceptance"] is False

    baseline = json.loads(lacuna.get_counterfactual_baseline(baseline_id))
    assert baseline["status"] == "PROPOSED"

    direct_vm.sender = direct_bob
    result = json.loads(lacuna.accept_baseline(agreement_id))
    assert result["status"] == "BASELINE_FINAL"
    assert result["client_baseline_acceptance"] is True
    assert result["contractor_baseline_acceptance"] is True

    baseline = json.loads(lacuna.get_counterfactual_baseline(baseline_id))
    assert baseline["status"] == "FINAL"


def test_accept_baseline_blocked_by_unresolved_challenge(direct_deploy, direct_vm, direct_alice, direct_bob):
    lacuna = direct_deploy("contracts/lacuna.py")
    agreement_id, _ = _proposed_agreement(lacuna, direct_vm, direct_alice, direct_bob)
    direct_vm.sender = direct_alice
    lacuna.open_baseline_challenge("CH-1", agreement_id, "EVIDENCE_OMITTED", "Statement.", [])

    with pytest.raises(Exception, match="BASELINE_PROPOSED"):
        lacuna.accept_baseline(agreement_id)


def test_accept_baseline_finalized_cannot_be_overwritten(direct_deploy, direct_vm, direct_alice, direct_bob):
    lacuna = direct_deploy("contracts/lacuna.py")
    agreement_id, baseline_id = _proposed_agreement(lacuna, direct_vm, direct_alice, direct_bob)
    direct_vm.sender = direct_alice
    lacuna.accept_baseline(agreement_id)
    direct_vm.sender = direct_bob
    lacuna.accept_baseline(agreement_id)

    with pytest.raises(Exception, match="BASELINE_PROPOSED"):
        lacuna.accept_baseline(agreement_id)

    with pytest.raises(Exception, match="BASELINE_FROZEN"):
        lacuna.evaluate_baseline(agreement_id)

    with pytest.raises(Exception, match="BASELINE_PROPOSED"):
        lacuna.open_baseline_challenge("CH-1", agreement_id, "EVIDENCE_OMITTED", "Too late.", [])

    baseline = json.loads(lacuna.get_counterfactual_baseline(baseline_id))
    assert baseline["status"] == "FINAL"
    assert baseline["expected_value_bps"] == 3400


def test_finalized_frozen_evidence_remains_immutable(direct_deploy, direct_vm, direct_alice, direct_bob):
    lacuna = direct_deploy("contracts/lacuna.py")
    agreement_id, _ = _proposed_agreement(lacuna, direct_vm, direct_alice, direct_bob)
    direct_vm.sender = direct_alice
    lacuna.accept_baseline(agreement_id)
    direct_vm.sender = direct_bob
    lacuna.accept_baseline(agreement_id)

    evidence = json.loads(lacuna.list_baseline_evidence(agreement_id))
    assert len(evidence) == 2
    assert all(item["status"] == "FROZEN" for item in evidence)
    ev1 = json.loads(lacuna.get_baseline_evidence("EV-1"))
    assert ev1["summary"] == "Historical churn dashboard export for the baseline window."


def test_accept_baseline_rejects_unauthorized_party(
    direct_deploy, direct_vm, direct_alice, direct_bob, direct_charlie
):
    lacuna = direct_deploy("contracts/lacuna.py")
    agreement_id, _ = _proposed_agreement(lacuna, direct_vm, direct_alice, direct_bob)

    direct_vm.sender = direct_charlie
    with pytest.raises(Exception, match="client or contractor"):
        lacuna.accept_baseline(agreement_id)


# =========================================================
# Observation lifecycle, outcome evidence, alternative
# explanations (Stage 6)
# =========================================================


def _finalized_agreement(lacuna, direct_vm, direct_alice, direct_bob, agreement_id="AGR-1", escrow_amount=10_000):
    """Agreement with a FINAL, dual-accepted baseline. BASELINE_FINAL,
    ready for start_observation()."""
    agreement_id, baseline_id = _proposed_agreement(
        lacuna, direct_vm, direct_alice, direct_bob,
        agreement_id=agreement_id, escrow_amount=escrow_amount
    )
    direct_vm.sender = direct_alice
    lacuna.accept_baseline(agreement_id)
    direct_vm.sender = direct_bob
    lacuna.accept_baseline(agreement_id)
    return agreement_id, baseline_id


def _observing_agreement(lacuna, direct_vm, direct_alice, direct_bob, agreement_id="AGR-1", escrow_amount=10_000):
    """Agreement in OBSERVING status, ready for outcome evidence /
    alternative explanation submission."""
    agreement_id, baseline_id = _finalized_agreement(
        lacuna, direct_vm, direct_alice, direct_bob,
        agreement_id=agreement_id, escrow_amount=escrow_amount
    )
    direct_vm.sender = direct_alice
    lacuna.start_observation(agreement_id)
    return agreement_id, baseline_id


def submit_outcome(
    lacuna,
    agreement_id="AGR-1",
    evidence_id="OUT-1",
    source_type="PUBLIC_ANALYTICS",
    source_url="https://analytics.example.com/outcome-report",
    content_hash=None,
    summary="Post-intervention churn dashboard export for the observation window.",
    metric_ref="monthly_churn_bps",
    observed_value_bps=1200,
    period_start=OBSERVATION_START + 100,
    period_end=OBSERVATION_START + 200,
):
    if content_hash is None:
        content_hash = _hash_of(evidence_id + source_url)
    return lacuna.submit_outcome_evidence(
        evidence_id,
        agreement_id,
        source_type,
        source_url,
        content_hash,
        summary,
        metric_ref,
        observed_value_bps,
        period_start,
        period_end,
    )


def _submit_full_outcome_evidence_set(lacuna, agreement_id):
    """Primary metric + both guardrail metrics covered, 3 items total --
    satisfies freeze_resolution's minimum-evidence, primary-metric, and
    guardrail-coverage requirements."""
    submit_outcome(
        lacuna,
        agreement_id=agreement_id,
        evidence_id="OUT-1",
        source_url="https://analytics.example.com/churn",
        metric_ref="monthly_churn_bps",
        observed_value_bps=1200,
        period_start=OBSERVATION_START + 100,
        period_end=OBSERVATION_START + 200,
    )
    submit_outcome(
        lacuna,
        agreement_id=agreement_id,
        evidence_id="OUT-2",
        source_url="https://community.example.org/retention",
        metric_ref="contributor_retention",
        observed_value_bps=6700,
        period_start=OBSERVATION_START + 300,
        period_end=OBSERVATION_START + 400,
    )
    submit_outcome(
        lacuna,
        agreement_id=agreement_id,
        evidence_id="OUT-3",
        source_url="https://community.example.org/activity",
        metric_ref="member_activity",
        observed_value_bps=5400,
        period_start=OBSERVATION_START + 500,
        period_end=OBSERVATION_START + 600,
    )


def submit_explanation(
    lacuna,
    agreement_id="AGR-1",
    explanation_id="EXP-1",
    explanation_type="PRODUCT_LAUNCH",
    statement="A major product update shipped mid-window and likely affected churn independently.",
    evidence_refs=None,
    affected_metrics=None,
    direction="POSITIVE",
    proposed_strength_bps=3000,
):
    if evidence_refs is None:
        evidence_refs = []
    if affected_metrics is None:
        affected_metrics = ["monthly_churn_bps"]
    return lacuna.submit_alternative_explanation(
        explanation_id,
        agreement_id,
        explanation_type,
        statement,
        evidence_refs,
        affected_metrics,
        direction,
        proposed_strength_bps,
    )


def test_start_observation_cannot_start_before_baseline_final(direct_deploy, direct_vm, direct_alice, direct_bob):
    lacuna = direct_deploy("contracts/lacuna.py")
    agreement_id, _ = _proposed_agreement(lacuna, direct_vm, direct_alice, direct_bob)
    direct_vm.sender = direct_alice

    with pytest.raises(Exception, match="BASELINE_FINAL"):
        lacuna.start_observation(agreement_id)


def test_start_observation_valid(direct_deploy, direct_vm, direct_alice, direct_bob):
    lacuna = direct_deploy("contracts/lacuna.py")
    agreement_id, baseline_id = _finalized_agreement(lacuna, direct_vm, direct_alice, direct_bob)
    direct_vm.sender = direct_alice

    result = json.loads(lacuna.start_observation(agreement_id))
    assert result["status"] == "OBSERVING"

    agreement = json.loads(lacuna.get_agreement(agreement_id))
    assert agreement["status"] == "OBSERVING"
    assert agreement["baseline_id"] == baseline_id


def test_start_observation_leaves_finalized_baseline_unchanged(direct_deploy, direct_vm, direct_alice, direct_bob):
    lacuna = direct_deploy("contracts/lacuna.py")
    agreement_id, baseline_id = _finalized_agreement(lacuna, direct_vm, direct_alice, direct_bob)
    before = json.loads(lacuna.get_counterfactual_baseline(baseline_id))

    direct_vm.sender = direct_alice
    lacuna.start_observation(agreement_id)

    after = json.loads(lacuna.get_counterfactual_baseline(baseline_id))
    assert after == before
    assert after["status"] == "FINAL"


def test_submit_outcome_evidence_valid(direct_deploy, direct_vm, direct_alice, direct_bob):
    lacuna = direct_deploy("contracts/lacuna.py")
    agreement_id, _ = _observing_agreement(lacuna, direct_vm, direct_alice, direct_bob)
    direct_vm.sender = direct_alice

    evidence_id = submit_outcome(lacuna, agreement_id=agreement_id)
    assert evidence_id == "OUT-1"
    assert lacuna.outcome_evidence_count == 1

    record = json.loads(lacuna.get_outcome_evidence("OUT-1"))
    assert record["agreement_id"] == agreement_id
    assert record["metric_ref"] == "monthly_churn_bps"
    assert record["observed_value_bps"] == 1200
    assert record["status"] == "SUBMITTED"
    assert record["source_host"] == "analytics.example.com"

    listed = json.loads(lacuna.list_outcome_evidence(agreement_id))
    assert len(listed) == 1

    agreement = json.loads(lacuna.get_agreement(agreement_id))
    assert agreement["status"] == "RESOLUTION_OPEN"


def test_submit_outcome_evidence_rejects_invalid_source_type(direct_deploy, direct_vm, direct_alice, direct_bob):
    lacuna = direct_deploy("contracts/lacuna.py")
    agreement_id, _ = _observing_agreement(lacuna, direct_vm, direct_alice, direct_bob)
    direct_vm.sender = direct_alice
    with pytest.raises(Exception, match="source_type"):
        submit_outcome(lacuna, agreement_id=agreement_id, source_type="NOT_A_REAL_CATEGORY")


def test_submit_outcome_evidence_rejects_invalid_url(direct_deploy, direct_vm, direct_alice, direct_bob):
    lacuna = direct_deploy("contracts/lacuna.py")
    agreement_id, _ = _observing_agreement(lacuna, direct_vm, direct_alice, direct_bob)
    direct_vm.sender = direct_alice
    with pytest.raises(Exception, match="source_url"):
        submit_outcome(lacuna, agreement_id=agreement_id, source_url="not-a-url")


def test_submit_outcome_evidence_rejects_invalid_content_hash(direct_deploy, direct_vm, direct_alice, direct_bob):
    lacuna = direct_deploy("contracts/lacuna.py")
    agreement_id, _ = _observing_agreement(lacuna, direct_vm, direct_alice, direct_bob)
    direct_vm.sender = direct_alice
    with pytest.raises(Exception, match="content_hash"):
        submit_outcome(lacuna, agreement_id=agreement_id, content_hash="not-a-hash")


def test_submit_outcome_evidence_rejects_invalid_metric(direct_deploy, direct_vm, direct_alice, direct_bob):
    lacuna = direct_deploy("contracts/lacuna.py")
    agreement_id, _ = _observing_agreement(lacuna, direct_vm, direct_alice, direct_bob)
    direct_vm.sender = direct_alice
    with pytest.raises(Exception, match="metric_ref"):
        submit_outcome(lacuna, agreement_id=agreement_id, metric_ref="not_in_constitution")


def test_submit_outcome_evidence_rejects_invalid_observed_bps(direct_deploy, direct_vm, direct_alice, direct_bob):
    lacuna = direct_deploy("contracts/lacuna.py")
    agreement_id, _ = _observing_agreement(lacuna, direct_vm, direct_alice, direct_bob)
    direct_vm.sender = direct_alice
    with pytest.raises(Exception, match="observed_value_bps"):
        submit_outcome(lacuna, agreement_id=agreement_id, observed_value_bps=10001)


def test_submit_outcome_evidence_rejects_invalid_period(direct_deploy, direct_vm, direct_alice, direct_bob):
    lacuna = direct_deploy("contracts/lacuna.py")
    agreement_id, _ = _observing_agreement(lacuna, direct_vm, direct_alice, direct_bob)
    direct_vm.sender = direct_alice
    with pytest.raises(Exception, match="period_start must be before period_end"):
        submit_outcome(lacuna, agreement_id=agreement_id, period_start=OBSERVATION_START + 200, period_end=OBSERVATION_START + 100)


def test_submit_outcome_evidence_rejects_period_outside_observation_window(
    direct_deploy, direct_vm, direct_alice, direct_bob
):
    lacuna = direct_deploy("contracts/lacuna.py")
    agreement_id, _ = _observing_agreement(lacuna, direct_vm, direct_alice, direct_bob)
    direct_vm.sender = direct_alice
    with pytest.raises(Exception, match="observation window"):
        submit_outcome(lacuna, agreement_id=agreement_id, period_start=BASELINE_START, period_end=BASELINE_START + 100)


def test_submit_outcome_evidence_rejects_duplicate_evidence_id(direct_deploy, direct_vm, direct_alice, direct_bob):
    lacuna = direct_deploy("contracts/lacuna.py")
    agreement_id, _ = _observing_agreement(lacuna, direct_vm, direct_alice, direct_bob)
    direct_vm.sender = direct_alice
    submit_outcome(lacuna, agreement_id=agreement_id, evidence_id="OUT-1")

    with pytest.raises(Exception, match="already exists"):
        submit_outcome(lacuna, agreement_id=agreement_id, evidence_id="OUT-1", source_url="https://analytics.example.com/other")


def test_submit_outcome_evidence_rejects_duplicate_content_hash(direct_deploy, direct_vm, direct_alice, direct_bob):
    lacuna = direct_deploy("contracts/lacuna.py")
    agreement_id, _ = _observing_agreement(lacuna, direct_vm, direct_alice, direct_bob)
    direct_vm.sender = direct_alice
    shared_hash = _hash_of("shared-outcome-content")
    submit_outcome(lacuna, agreement_id=agreement_id, evidence_id="OUT-1", content_hash=shared_hash)

    with pytest.raises(Exception, match="Duplicate evidence"):
        submit_outcome(
            lacuna,
            agreement_id=agreement_id,
            evidence_id="OUT-2",
            source_url="https://analytics.example.com/other",
            content_hash=shared_hash,
        )


def test_submit_outcome_evidence_cap_enforced(direct_deploy, direct_vm, direct_alice, direct_bob):
    lacuna = direct_deploy("contracts/lacuna.py")
    agreement_id, _ = _observing_agreement(lacuna, direct_vm, direct_alice, direct_bob)
    direct_vm.sender = direct_alice

    for i in range(48):
        submit_outcome(
            lacuna,
            agreement_id=agreement_id,
            evidence_id=f"OUT-{i}",
            source_url=f"https://analytics.example.com/outcome-{i}",
            period_start=OBSERVATION_START + i * 10,
            period_end=OBSERVATION_START + i * 10 + 5,
        )

    assert lacuna.outcome_evidence_count == 48

    with pytest.raises(Exception, match="cap reached"):
        submit_outcome(
            lacuna,
            agreement_id=agreement_id,
            evidence_id="OUT-overflow",
            source_url="https://analytics.example.com/outcome-overflow",
            period_start=OBSERVATION_START + 10000,
            period_end=OBSERVATION_START + 10005,
        )


def test_submit_alternative_explanation_valid(direct_deploy, direct_vm, direct_alice, direct_bob):
    lacuna = direct_deploy("contracts/lacuna.py")
    agreement_id, _ = _observing_agreement(lacuna, direct_vm, direct_alice, direct_bob)
    direct_vm.sender = direct_alice
    submit_outcome(lacuna, agreement_id=agreement_id, evidence_id="OUT-1")

    explanation_id = submit_explanation(
        lacuna, agreement_id=agreement_id, evidence_refs=["OUT-1"], affected_metrics=["monthly_churn_bps"]
    )
    assert explanation_id == "EXP-1"
    assert lacuna.alternative_explanation_count == 1

    record = json.loads(lacuna.get_alternative_explanation("EXP-1"))
    assert record["explanation_type"] == "PRODUCT_LAUNCH"
    assert record["evidence_refs"] == ["OUT-1"]
    assert record["affected_metrics"] == ["monthly_churn_bps"]
    assert record["direction"] == "POSITIVE"
    assert record["proposed_strength_bps"] == 3000
    assert record["status"] == "SUBMITTED"

    listed = json.loads(lacuna.list_explanations(agreement_id))
    assert len(listed) == 1
    assert listed[0]["explanation_id"] == "EXP-1"


def test_submit_alternative_explanation_can_cite_frozen_baseline_evidence(
    direct_deploy, direct_vm, direct_alice, direct_bob
):
    lacuna = direct_deploy("contracts/lacuna.py")
    agreement_id, _ = _observing_agreement(lacuna, direct_vm, direct_alice, direct_bob)
    direct_vm.sender = direct_alice

    # EV-1/EV-2 are the frozen baseline evidence submitted during
    # _ready_for_baseline_evaluation -- citing pre-trend evidence from
    # before the observation window is a legitimate explanation design.
    explanation_id = submit_explanation(
        lacuna,
        agreement_id=agreement_id,
        explanation_type="SEASONALITY",
        evidence_refs=["EV-1"],
        affected_metrics=["monthly_churn_bps"],
    )
    record = json.loads(lacuna.get_alternative_explanation(explanation_id))
    assert record["evidence_refs"] == ["EV-1"]


def test_submit_alternative_explanation_rejects_unsupported_type(direct_deploy, direct_vm, direct_alice, direct_bob):
    lacuna = direct_deploy("contracts/lacuna.py")
    agreement_id, _ = _observing_agreement(lacuna, direct_vm, direct_alice, direct_bob)
    direct_vm.sender = direct_alice
    with pytest.raises(Exception, match="explanation_type"):
        submit_explanation(lacuna, agreement_id=agreement_id, explanation_type="NOT_A_REAL_TYPE")


def test_submit_alternative_explanation_rejects_invalid_strength(direct_deploy, direct_vm, direct_alice, direct_bob):
    lacuna = direct_deploy("contracts/lacuna.py")
    agreement_id, _ = _observing_agreement(lacuna, direct_vm, direct_alice, direct_bob)
    direct_vm.sender = direct_alice
    with pytest.raises(Exception, match="proposed_strength_bps"):
        submit_explanation(lacuna, agreement_id=agreement_id, proposed_strength_bps=10001)


def test_submit_alternative_explanation_rejects_invalid_affected_metric(
    direct_deploy, direct_vm, direct_alice, direct_bob
):
    lacuna = direct_deploy("contracts/lacuna.py")
    agreement_id, _ = _observing_agreement(lacuna, direct_vm, direct_alice, direct_bob)
    direct_vm.sender = direct_alice
    with pytest.raises(Exception, match="affected_metrics"):
        submit_explanation(lacuna, agreement_id=agreement_id, affected_metrics=["not_a_real_metric"])


def test_submit_alternative_explanation_rejects_invalid_evidence_ref(
    direct_deploy, direct_vm, direct_alice, direct_bob
):
    lacuna = direct_deploy("contracts/lacuna.py")
    agreement_id, _ = _observing_agreement(lacuna, direct_vm, direct_alice, direct_bob)
    direct_vm.sender = direct_alice
    with pytest.raises(Exception, match="evidence_refs references evidence outside"):
        submit_explanation(lacuna, agreement_id=agreement_id, evidence_refs=["does-not-exist"])


def test_submit_alternative_explanation_rejects_duplicate_evidence_refs(
    direct_deploy, direct_vm, direct_alice, direct_bob
):
    lacuna = direct_deploy("contracts/lacuna.py")
    agreement_id, _ = _observing_agreement(lacuna, direct_vm, direct_alice, direct_bob)
    direct_vm.sender = direct_alice
    with pytest.raises(Exception, match="duplicate references"):
        submit_explanation(lacuna, agreement_id=agreement_id, evidence_refs=["EV-1", "EV-1"])


def test_submitted_explanation_is_only_a_claim_not_authoritative(direct_deploy, direct_vm, direct_alice, direct_bob):
    """proposed_strength_bps must be stored as the submitter's assertion
    only -- nothing in submit_alternative_explanation writes it anywhere
    that represents adjudicated attribution (no AttributionVerdict exists
    yet; that is Stage 7). This test asserts the explanation record itself
    carries no adjudication fields and the agreement/baseline are untouched."""
    lacuna = direct_deploy("contracts/lacuna.py")
    agreement_id, baseline_id = _observing_agreement(lacuna, direct_vm, direct_alice, direct_bob)
    baseline_before = json.loads(lacuna.get_counterfactual_baseline(baseline_id))
    agreement_before = json.loads(lacuna.get_agreement(agreement_id))

    direct_vm.sender = direct_alice
    submit_explanation(lacuna, agreement_id=agreement_id, proposed_strength_bps=9999)

    baseline_after = json.loads(lacuna.get_counterfactual_baseline(baseline_id))
    agreement_after = json.loads(lacuna.get_agreement(agreement_id))
    assert baseline_after == baseline_before
    # only the ordinary lazy OBSERVING -> RESOLUTION_OPEN lifecycle
    # transition may occur -- nothing else about the agreement changes,
    # and no verdict of any kind is created from an explanation alone.
    assert agreement_before["status"] == "OBSERVING"
    assert agreement_after["status"] == "RESOLUTION_OPEN"
    assert agreement_after["baseline_id"] == agreement_before["baseline_id"]
    assert lacuna.verdict_count == 0


def test_freeze_resolution_succeeds(direct_deploy, direct_vm, direct_alice, direct_bob):
    lacuna = direct_deploy("contracts/lacuna.py")
    agreement_id, baseline_id = _observing_agreement(lacuna, direct_vm, direct_alice, direct_bob)
    direct_vm.sender = direct_alice
    _submit_full_outcome_evidence_set(lacuna, agreement_id)
    submit_explanation(lacuna, agreement_id=agreement_id, evidence_refs=["OUT-1"])
    _mock_outcome_snapshots(direct_vm)

    result = lacuna.freeze_resolution(agreement_id)
    assert result == agreement_id

    agreement = json.loads(lacuna.get_agreement(agreement_id))
    assert agreement["status"] == "RESOLUTION_FROZEN"

    evidence = json.loads(lacuna.list_outcome_evidence(agreement_id))
    assert len(evidence) == 3
    assert all(item["status"] == "FROZEN" for item in evidence)
    assert all(item["content_hash"] == _hash_of(item["frozen_content"]) for item in evidence)

    explanations = json.loads(lacuna.list_explanations(agreement_id))
    assert len(explanations) == 1
    assert explanations[0]["status"] == "FROZEN"

    # finalized baseline preserved untouched
    baseline = json.loads(lacuna.get_counterfactual_baseline(baseline_id))
    assert baseline["status"] == "FINAL"
    assert baseline["expected_value_bps"] == 3400


def test_freeze_resolution_rejects_unrelated_wallet(
    direct_deploy, direct_vm, direct_alice, direct_bob, direct_charlie,
):
    lacuna = direct_deploy("contracts/lacuna.py")
    agreement_id, _ = _observing_agreement(lacuna, direct_vm, direct_alice, direct_bob)
    direct_vm.sender = direct_alice
    _submit_full_outcome_evidence_set(lacuna, agreement_id)
    direct_vm.sender = direct_charlie
    with pytest.raises(Exception, match="client or contractor"):
        lacuna.freeze_resolution(agreement_id)


def test_freeze_resolution_without_primary_metric_evidence_rejected(
    direct_deploy, direct_vm, direct_alice, direct_bob
):
    lacuna = direct_deploy("contracts/lacuna.py")
    agreement_id, _ = _observing_agreement(lacuna, direct_vm, direct_alice, direct_bob)
    direct_vm.sender = direct_alice
    submit_outcome(
        lacuna, agreement_id=agreement_id, evidence_id="OUT-1",
        source_url="https://community.example.org/retention", metric_ref="contributor_retention",
    )
    submit_outcome(
        lacuna, agreement_id=agreement_id, evidence_id="OUT-2",
        source_url="https://community.example.org/activity", metric_ref="member_activity",
        period_start=OBSERVATION_START + 300, period_end=OBSERVATION_START + 400,
    )

    with pytest.raises(Exception, match="primary metric"):
        lacuna.freeze_resolution(agreement_id)


def test_freeze_resolution_requires_guardrail_evidence(direct_deploy, direct_vm, direct_alice, direct_bob):
    lacuna = direct_deploy("contracts/lacuna.py")
    agreement_id, _ = _observing_agreement(lacuna, direct_vm, direct_alice, direct_bob)
    direct_vm.sender = direct_alice
    submit_outcome(
        lacuna, agreement_id=agreement_id, evidence_id="OUT-1",
        source_url="https://analytics.example.com/churn", metric_ref="monthly_churn_bps",
    )
    submit_outcome(
        lacuna, agreement_id=agreement_id, evidence_id="OUT-2",
        source_url="https://community.example.org/retention", metric_ref="contributor_retention",
        period_start=OBSERVATION_START + 300, period_end=OBSERVATION_START + 400,
    )
    # member_activity guardrail never submitted

    with pytest.raises(Exception, match="guardrail metric"):
        lacuna.freeze_resolution(agreement_id)


def test_freeze_resolution_requires_sufficient_evidence(direct_deploy, direct_vm, direct_alice, direct_bob):
    lacuna = direct_deploy("contracts/lacuna.py")
    agreement_id, _ = _observing_agreement(lacuna, direct_vm, direct_alice, direct_bob)
    direct_vm.sender = direct_alice
    # never submits anything -- status stays OBSERVING, freeze must fail

    with pytest.raises(Exception, match="RESOLUTION_OPEN"):
        lacuna.freeze_resolution(agreement_id)


def test_no_outcome_evidence_can_be_submitted_after_freeze(direct_deploy, direct_vm, direct_alice, direct_bob):
    lacuna = direct_deploy("contracts/lacuna.py")
    agreement_id, _ = _observing_agreement(lacuna, direct_vm, direct_alice, direct_bob)
    direct_vm.sender = direct_alice
    _submit_full_outcome_evidence_set(lacuna, agreement_id)
    _mock_outcome_snapshots(direct_vm)
    lacuna.freeze_resolution(agreement_id)

    with pytest.raises(Exception, match="OBSERVING or RESOLUTION_OPEN"):
        submit_outcome(lacuna, agreement_id=agreement_id, evidence_id="OUT-4")


def test_no_explanation_can_be_submitted_after_freeze(direct_deploy, direct_vm, direct_alice, direct_bob):
    lacuna = direct_deploy("contracts/lacuna.py")
    agreement_id, _ = _observing_agreement(lacuna, direct_vm, direct_alice, direct_bob)
    direct_vm.sender = direct_alice
    _submit_full_outcome_evidence_set(lacuna, agreement_id)
    _mock_outcome_snapshots(direct_vm)
    lacuna.freeze_resolution(agreement_id)

    with pytest.raises(Exception, match="OBSERVING or RESOLUTION_OPEN"):
        submit_explanation(lacuna, agreement_id=agreement_id, explanation_id="EXP-late")


def test_frozen_resolution_records_remain_queryable_and_immutable(
    direct_deploy, direct_vm, direct_alice, direct_bob
):
    lacuna = direct_deploy("contracts/lacuna.py")
    agreement_id, _ = _observing_agreement(lacuna, direct_vm, direct_alice, direct_bob)
    direct_vm.sender = direct_alice
    _submit_full_outcome_evidence_set(lacuna, agreement_id)
    submit_explanation(lacuna, agreement_id=agreement_id, evidence_refs=["OUT-1"])
    _mock_outcome_snapshots(direct_vm)
    lacuna.freeze_resolution(agreement_id)

    evidence = json.loads(lacuna.get_outcome_evidence("OUT-1"))
    assert evidence["status"] == "FROZEN"
    assert evidence["observed_value_bps"] == 1200

    explanation = json.loads(lacuna.get_alternative_explanation("EXP-1"))
    assert explanation["status"] == "FROZEN"
    assert explanation["proposed_strength_bps"] == 3000


# =========================================================
# AttributionVerdict adjudication (Stage 7)
# =========================================================


def _resolved_agreement(lacuna, direct_vm, direct_alice, direct_bob, agreement_id="AGR-1", escrow_amount=10_000):
    """Agreement with a full frozen resolution package -- baseline evidence,
    outcome evidence (primary + both guardrails), one explanation -- and
    every evidence source_url mocked. Ready for evaluate_performance()."""
    agreement_id, baseline_id = _observing_agreement(
        lacuna, direct_vm, direct_alice, direct_bob,
        agreement_id=agreement_id, escrow_amount=escrow_amount
    )
    direct_vm.sender = direct_alice
    _submit_full_outcome_evidence_set(lacuna, agreement_id)
    submit_explanation(lacuna, agreement_id=agreement_id, evidence_refs=["OUT-1"])
    _mock_outcome_snapshots(direct_vm)
    lacuna.freeze_resolution(agreement_id)
    return agreement_id, baseline_id


PERFORMANCE_VERDICT_BASE = {
    "baseline_expected_bps": 3400,
    "baseline_low_bps": 2900,
    "baseline_high_bps": 4100,
    "observed_value_bps": 1200,
    "meaningful_deviation_bps": 2200,
    "deviation_confidence_bps": 9200,
    "attribution_bps": 8200,
    "evidence_confidence_bps": 9000,
    "alternative_explanation_strength_bps": 1000,
    "guardrail_penalty_bps": 0,
    "performance_bps": 8200,
    "reason_codes": ["OUTCOME_EXCEEDS_EXPECTED_RANGE", "PERSISTENCE_SUPPORTS_ATTRIBUTION", "GUARDRAILS_PRESERVED"],
    "evidence_refs": ["OUT-1"],
    "summary": "Outcome substantially beats the locked baseline with strong, persistent, well-corroborated evidence of contractor action.",
}

LOW_ATTRIBUTION_VERDICT = dict(
    PERFORMANCE_VERDICT_BASE,
    attribution_bps=1500,
    alternative_explanation_strength_bps=8000,
    performance_bps=1200,
    reason_codes=["OUTCOME_EXCEEDS_EXPECTED_RANGE", "ALTERNATIVE_EXPLANATION_DOMINANT"],
    summary="Outcome exceeds the baseline but a dominant competing explanation leaves little credible contractor attribution.",
)

NOT_OUTSIDE_BASELINE_VERDICT = dict(
    PERFORMANCE_VERDICT_BASE,
    meaningful_deviation_bps=0,
    deviation_confidence_bps=9000,
    attribution_bps=0,
    alternative_explanation_strength_bps=0,
    performance_bps=0,
    reason_codes=["OUTCOME_NOT_OUTSIDE_EXPECTED_RANGE"],
    summary="The observed value falls within the locked baseline's expected range; no meaningful deviation to attribute.",
)

PRODUCT_LAUNCH_VERDICT = dict(
    PERFORMANCE_VERDICT_BASE,
    attribution_bps=2000,
    alternative_explanation_strength_bps=7500,
    performance_bps=2000,
    reason_codes=["OUTCOME_EXCEEDS_EXPECTED_RANGE", "PRODUCT_LAUNCH_CONFOUNDER"],
    summary="A product launch during the window plausibly explains most of the improvement.",
)

MARKET_EFFECT_VERDICT = dict(
    PERFORMANCE_VERDICT_BASE,
    attribution_bps=1800,
    alternative_explanation_strength_bps=8000,
    performance_bps=1800,
    reason_codes=["OUTCOME_EXCEEDS_EXPECTED_RANGE", "MARKET_EFFECT_STRONG"],
    summary="A market-wide effect independent of the contractor dominates the observed improvement.",
)

OTHER_TEAM_VERDICT = dict(
    PERFORMANCE_VERDICT_BASE,
    attribution_bps=1900,
    alternative_explanation_strength_bps=7800,
    performance_bps=1900,
    reason_codes=["OUTCOME_EXCEEDS_EXPECTED_RANGE", "OTHER_TEAM_EFFECT_STRONG"],
    summary="Evidence indicates another team's intervention is the stronger explanation for the improvement.",
)

PRE_TREND_VERDICT = dict(
    PERFORMANCE_VERDICT_BASE,
    attribution_bps=1500,
    alternative_explanation_strength_bps=8200,
    performance_bps=1500,
    reason_codes=["OUTCOME_EXCEEDS_EXPECTED_RANGE", "PRE_TREND_ALREADY_IMPROVING"],
    summary="The metric was already trending favorably before the observation window began.",
)

MEASUREMENT_METHOD_VERDICT = dict(
    PERFORMANCE_VERDICT_BASE,
    deviation_confidence_bps=3000,
    evidence_confidence_bps=2000,
    attribution_bps=1000,
    alternative_explanation_strength_bps=8000,
    performance_bps=1000,
    reason_codes=["MEASUREMENT_METHOD_CHANGED", "EVIDENCE_CONFIDENCE_LOW"],
    summary="The measurement methodology changed between the baseline and observation windows, undermining comparability.",
)

MEMBERSHIP_COMPOSITION_VERDICT = dict(
    PERFORMANCE_VERDICT_BASE,
    attribution_bps=1700,
    alternative_explanation_strength_bps=7900,
    performance_bps=1700,
    reason_codes=["OUTCOME_EXCEEDS_EXPECTED_RANGE", "MEMBERSHIP_COMPOSITION_CHANGED"],
    summary="A significant shift in membership composition confounds the observed improvement.",
)

GUARDRAIL_VIOLATION_VERDICT = dict(
    PERFORMANCE_VERDICT_BASE,
    guardrail_penalty_bps=3000,
    attribution_bps=8000,
    performance_bps=5000,
    reason_codes=["OUTCOME_EXCEEDS_EXPECTED_RANGE", "GUARDRAIL_VIOLATION"],
    summary="The primary metric improved but guardrail metrics deteriorated materially; performance is penalized accordingly.",
)

METRIC_GAMING_VERDICT = dict(
    PERFORMANCE_VERDICT_BASE,
    attribution_bps=1200,
    alternative_explanation_strength_bps=6000,
    performance_bps=1200,
    reason_codes=["METRIC_GAMING_SUSPECTED", "EVIDENCE_CONFIDENCE_LOW"],
    summary="The pattern of evidence is consistent with metric gaming rather than genuine improvement.",
)


def test_evaluate_performance_valid_high_attribution(direct_deploy, direct_vm, direct_alice, direct_bob):
    lacuna = direct_deploy("contracts/lacuna.py")
    agreement_id, baseline_id = _resolved_agreement(lacuna, direct_vm, direct_alice, direct_bob)
    direct_vm.mock_llm(r".*", _fenced(PERFORMANCE_VERDICT_BASE))

    result = json.loads(lacuna.evaluate_performance(agreement_id))
    assert result["attribution_bps"] == 8200
    assert result["performance_bps"] == 8200
    assert result["baseline_expected_bps"] == 3400
    assert result["status"] == "PROPOSED"

    agreement = json.loads(lacuna.get_agreement(agreement_id))
    assert agreement["status"] == "VERDICT_PROPOSED"
    assert agreement["verdict_id"] == result["verdict_id"]

    verdict = json.loads(lacuna.get_verdict(result["verdict_id"]))
    assert verdict["performance_bps"] == 8200


def test_evaluate_performance_valid_low_attribution(direct_deploy, direct_vm, direct_alice, direct_bob):
    lacuna = direct_deploy("contracts/lacuna.py")
    agreement_id, _ = _resolved_agreement(lacuna, direct_vm, direct_alice, direct_bob)
    direct_vm.mock_llm(r".*", _fenced(LOW_ATTRIBUTION_VERDICT))

    result = json.loads(lacuna.evaluate_performance(agreement_id))
    assert result["attribution_bps"] == 1500
    assert result["reason_codes"] == ["OUTCOME_EXCEEDS_EXPECTED_RANGE", "ALTERNATIVE_EXPLANATION_DOMINANT"]


def test_evaluate_performance_observed_outcome_not_outside_baseline(direct_deploy, direct_vm, direct_alice, direct_bob):
    lacuna = direct_deploy("contracts/lacuna.py")
    agreement_id, _ = _resolved_agreement(lacuna, direct_vm, direct_alice, direct_bob)
    direct_vm.mock_llm(r".*", _fenced(NOT_OUTSIDE_BASELINE_VERDICT))

    result = json.loads(lacuna.evaluate_performance(agreement_id))
    assert result["reason_codes"] == ["OUTCOME_NOT_OUTSIDE_EXPECTED_RANGE"]
    assert result["attribution_bps"] == 0
    assert result["performance_bps"] == 0


def test_evaluate_performance_dominant_product_launch_confounder(direct_deploy, direct_vm, direct_alice, direct_bob):
    lacuna = direct_deploy("contracts/lacuna.py")
    agreement_id, _ = _resolved_agreement(lacuna, direct_vm, direct_alice, direct_bob)
    direct_vm.mock_llm(r".*", _fenced(PRODUCT_LAUNCH_VERDICT))

    result = json.loads(lacuna.evaluate_performance(agreement_id))
    assert "PRODUCT_LAUNCH_CONFOUNDER" in result["reason_codes"]
    assert result["alternative_explanation_strength_bps"] == 7500


def test_evaluate_performance_strong_market_wide_confounder(direct_deploy, direct_vm, direct_alice, direct_bob):
    lacuna = direct_deploy("contracts/lacuna.py")
    agreement_id, _ = _resolved_agreement(lacuna, direct_vm, direct_alice, direct_bob)
    direct_vm.mock_llm(r".*", _fenced(MARKET_EFFECT_VERDICT))

    result = json.loads(lacuna.evaluate_performance(agreement_id))
    assert "MARKET_EFFECT_STRONG" in result["reason_codes"]


def test_evaluate_performance_other_team_intervention(direct_deploy, direct_vm, direct_alice, direct_bob):
    lacuna = direct_deploy("contracts/lacuna.py")
    agreement_id, _ = _resolved_agreement(lacuna, direct_vm, direct_alice, direct_bob)
    direct_vm.mock_llm(r".*", _fenced(OTHER_TEAM_VERDICT))

    result = json.loads(lacuna.evaluate_performance(agreement_id))
    assert "OTHER_TEAM_EFFECT_STRONG" in result["reason_codes"]


def test_evaluate_performance_pre_trend_already_improving(direct_deploy, direct_vm, direct_alice, direct_bob):
    lacuna = direct_deploy("contracts/lacuna.py")
    agreement_id, _ = _resolved_agreement(lacuna, direct_vm, direct_alice, direct_bob)
    direct_vm.mock_llm(r".*", _fenced(PRE_TREND_VERDICT))

    result = json.loads(lacuna.evaluate_performance(agreement_id))
    assert "PRE_TREND_ALREADY_IMPROVING" in result["reason_codes"]


def test_evaluate_performance_measurement_methodology_changed(direct_deploy, direct_vm, direct_alice, direct_bob):
    lacuna = direct_deploy("contracts/lacuna.py")
    agreement_id, _ = _resolved_agreement(lacuna, direct_vm, direct_alice, direct_bob)
    direct_vm.mock_llm(r".*", _fenced(MEASUREMENT_METHOD_VERDICT))

    result = json.loads(lacuna.evaluate_performance(agreement_id))
    assert "MEASUREMENT_METHOD_CHANGED" in result["reason_codes"]


def test_evaluate_performance_membership_composition_changed(direct_deploy, direct_vm, direct_alice, direct_bob):
    lacuna = direct_deploy("contracts/lacuna.py")
    agreement_id, _ = _resolved_agreement(lacuna, direct_vm, direct_alice, direct_bob)
    direct_vm.mock_llm(r".*", _fenced(MEMBERSHIP_COMPOSITION_VERDICT))

    result = json.loads(lacuna.evaluate_performance(agreement_id))
    assert "MEMBERSHIP_COMPOSITION_CHANGED" in result["reason_codes"]


def test_evaluate_performance_guardrail_violation(direct_deploy, direct_vm, direct_alice, direct_bob):
    lacuna = direct_deploy("contracts/lacuna.py")
    agreement_id, _ = _resolved_agreement(lacuna, direct_vm, direct_alice, direct_bob)
    direct_vm.mock_llm(r".*", _fenced(GUARDRAIL_VIOLATION_VERDICT))

    result = json.loads(lacuna.evaluate_performance(agreement_id))
    assert "GUARDRAIL_VIOLATION" in result["reason_codes"]
    assert result["guardrail_penalty_bps"] == 3000
    assert result["performance_bps"] <= result["attribution_bps"]


def test_evaluate_performance_metric_gaming_suspected(direct_deploy, direct_vm, direct_alice, direct_bob):
    lacuna = direct_deploy("contracts/lacuna.py")
    agreement_id, _ = _resolved_agreement(lacuna, direct_vm, direct_alice, direct_bob)
    direct_vm.mock_llm(r".*", _fenced(METRIC_GAMING_VERDICT))

    result = json.loads(lacuna.evaluate_performance(agreement_id))
    assert "METRIC_GAMING_SUSPECTED" in result["reason_codes"]


def test_evaluate_performance_persistence_supports_attribution(direct_deploy, direct_vm, direct_alice, direct_bob):
    lacuna = direct_deploy("contracts/lacuna.py")
    agreement_id, _ = _resolved_agreement(lacuna, direct_vm, direct_alice, direct_bob)
    direct_vm.mock_llm(r".*", _fenced(PERFORMANCE_VERDICT_BASE))

    result = json.loads(lacuna.evaluate_performance(agreement_id))
    assert "PERSISTENCE_SUPPORTS_ATTRIBUTION" in result["reason_codes"]


def test_evaluate_performance_negative_space_case(direct_deploy, direct_vm, direct_alice, direct_bob):
    """Negative-space guidance is textual (prompt-level), not enforced by
    a special contract code path -- the strict schema/validation is
    identical for a 'fewer bad outcomes' story as for a 'more good outcomes'
    story. This asserts a negative-space-framed verdict is accepted exactly
    like any other valid verdict, proving no special-casing is needed or done."""
    lacuna = direct_deploy("contracts/lacuna.py")
    agreement_id, _ = _resolved_agreement(lacuna, direct_vm, direct_alice, direct_bob)
    negative_space_verdict = dict(
        PERFORMANCE_VERDICT_BASE,
        summary="Churn (a negative outcome) fell well below the expected range; this is treated as an "
                "evidence-based deviation assessment, not proof a specific number of departures was prevented.",
    )
    direct_vm.mock_llm(r".*", _fenced(negative_space_verdict))

    result = json.loads(lacuna.evaluate_performance(agreement_id))
    assert result["status"] == "PROPOSED"


def test_evaluate_performance_rejects_malformed_json(direct_deploy, direct_vm, direct_alice, direct_bob):
    lacuna = direct_deploy("contracts/lacuna.py")
    agreement_id, _ = _resolved_agreement(lacuna, direct_vm, direct_alice, direct_bob)
    direct_vm.mock_llm(r".*", "not json")

    with pytest.raises(Exception, match="not valid JSON"):
        lacuna.evaluate_performance(agreement_id)


def test_evaluate_performance_rejects_non_object_json(direct_deploy, direct_vm, direct_alice, direct_bob):
    lacuna = direct_deploy("contracts/lacuna.py")
    agreement_id, _ = _resolved_agreement(lacuna, direct_vm, direct_alice, direct_bob)
    direct_vm.mock_llm(r".*", _fenced([1, 2, 3]))

    with pytest.raises(Exception, match="expected a JSON object"):
        lacuna.evaluate_performance(agreement_id)


def test_evaluate_performance_rejects_missing_field(direct_deploy, direct_vm, direct_alice, direct_bob):
    lacuna = direct_deploy("contracts/lacuna.py")
    agreement_id, _ = _resolved_agreement(lacuna, direct_vm, direct_alice, direct_bob)
    bad = dict(PERFORMANCE_VERDICT_BASE)
    del bad["summary"]
    direct_vm.mock_llm(r".*", _fenced(bad))

    with pytest.raises(Exception, match="missing field 'summary'"):
        lacuna.evaluate_performance(agreement_id)


def test_evaluate_performance_rejects_wrong_field_type(direct_deploy, direct_vm, direct_alice, direct_bob):
    lacuna = direct_deploy("contracts/lacuna.py")
    agreement_id, _ = _resolved_agreement(lacuna, direct_vm, direct_alice, direct_bob)
    bad = dict(PERFORMANCE_VERDICT_BASE, attribution_bps="high")
    direct_vm.mock_llm(r".*", _fenced(bad))

    with pytest.raises(Exception, match="attribution_bps must be an integer"):
        lacuna.evaluate_performance(agreement_id)


def test_evaluate_performance_rejects_bps_below_zero(direct_deploy, direct_vm, direct_alice, direct_bob):
    lacuna = direct_deploy("contracts/lacuna.py")
    agreement_id, _ = _resolved_agreement(lacuna, direct_vm, direct_alice, direct_bob)
    bad = dict(PERFORMANCE_VERDICT_BASE, guardrail_penalty_bps=-1)
    direct_vm.mock_llm(r".*", _fenced(bad))

    with pytest.raises(Exception, match="guardrail_penalty_bps must be between 0 and 10000"):
        lacuna.evaluate_performance(agreement_id)


def test_evaluate_performance_rejects_bps_above_10000(direct_deploy, direct_vm, direct_alice, direct_bob):
    lacuna = direct_deploy("contracts/lacuna.py")
    agreement_id, _ = _resolved_agreement(lacuna, direct_vm, direct_alice, direct_bob)
    bad = dict(PERFORMANCE_VERDICT_BASE, evidence_confidence_bps=10001)
    direct_vm.mock_llm(r".*", _fenced(bad))

    with pytest.raises(Exception, match="evidence_confidence_bps must be between 0 and 10000"):
        lacuna.evaluate_performance(agreement_id)


def test_evaluate_performance_rejects_altered_baseline_expected(direct_deploy, direct_vm, direct_alice, direct_bob):
    lacuna = direct_deploy("contracts/lacuna.py")
    agreement_id, _ = _resolved_agreement(lacuna, direct_vm, direct_alice, direct_bob)
    bad = dict(PERFORMANCE_VERDICT_BASE, baseline_expected_bps=9999)
    direct_vm.mock_llm(r".*", _fenced(bad))

    with pytest.raises(Exception, match="baseline_expected_bps must exactly match the locked baseline"):
        lacuna.evaluate_performance(agreement_id)


def test_evaluate_performance_rejects_altered_baseline_low(direct_deploy, direct_vm, direct_alice, direct_bob):
    lacuna = direct_deploy("contracts/lacuna.py")
    agreement_id, _ = _resolved_agreement(lacuna, direct_vm, direct_alice, direct_bob)
    bad = dict(PERFORMANCE_VERDICT_BASE, baseline_low_bps=1000)
    direct_vm.mock_llm(r".*", _fenced(bad))

    with pytest.raises(Exception, match="baseline_low_bps must exactly match the locked baseline"):
        lacuna.evaluate_performance(agreement_id)


def test_evaluate_performance_rejects_altered_baseline_high(direct_deploy, direct_vm, direct_alice, direct_bob):
    lacuna = direct_deploy("contracts/lacuna.py")
    agreement_id, _ = _resolved_agreement(lacuna, direct_vm, direct_alice, direct_bob)
    bad = dict(PERFORMANCE_VERDICT_BASE, baseline_high_bps=9999)
    direct_vm.mock_llm(r".*", _fenced(bad))

    with pytest.raises(Exception, match="baseline_high_bps must exactly match the locked baseline"):
        lacuna.evaluate_performance(agreement_id)


def test_evaluate_performance_rejects_observed_value_unsupported_by_evidence(
    direct_deploy, direct_vm, direct_alice, direct_bob
):
    lacuna = direct_deploy("contracts/lacuna.py")
    agreement_id, _ = _resolved_agreement(lacuna, direct_vm, direct_alice, direct_bob)
    bad = dict(PERFORMANCE_VERDICT_BASE, observed_value_bps=5000)  # only OUT-1 (1200) supports this metric
    direct_vm.mock_llm(r".*", _fenced(bad))

    with pytest.raises(Exception, match="observed_value_bps must fall within the range reported by frozen outcome evidence"):
        lacuna.evaluate_performance(agreement_id)


def test_evaluate_performance_rejects_unknown_reason_code(direct_deploy, direct_vm, direct_alice, direct_bob):
    lacuna = direct_deploy("contracts/lacuna.py")
    agreement_id, _ = _resolved_agreement(lacuna, direct_vm, direct_alice, direct_bob)
    bad = dict(PERFORMANCE_VERDICT_BASE, reason_codes=["NOT_A_REAL_CODE"])
    direct_vm.mock_llm(r".*", _fenced(bad))

    with pytest.raises(Exception, match="Unknown reason code: NOT_A_REAL_CODE"):
        lacuna.evaluate_performance(agreement_id)


def test_evaluate_performance_rejects_nonexistent_evidence_ref(direct_deploy, direct_vm, direct_alice, direct_bob):
    lacuna = direct_deploy("contracts/lacuna.py")
    agreement_id, _ = _resolved_agreement(lacuna, direct_vm, direct_alice, direct_bob)
    bad = dict(PERFORMANCE_VERDICT_BASE, evidence_refs=["OUT-does-not-exist"])
    direct_vm.mock_llm(r".*", _fenced(bad))

    with pytest.raises(Exception, match="evidence_refs references evidence outside the frozen resolution package"):
        lacuna.evaluate_performance(agreement_id)


def test_evaluate_performance_rejects_duplicate_evidence_ref(direct_deploy, direct_vm, direct_alice, direct_bob):
    lacuna = direct_deploy("contracts/lacuna.py")
    agreement_id, _ = _resolved_agreement(lacuna, direct_vm, direct_alice, direct_bob)
    bad = dict(PERFORMANCE_VERDICT_BASE, evidence_refs=["OUT-1", "OUT-1"])
    direct_vm.mock_llm(r".*", _fenced(bad))

    with pytest.raises(Exception, match="evidence_refs must not contain duplicate references"):
        lacuna.evaluate_performance(agreement_id)


def test_evaluate_performance_rejects_empty_summary(direct_deploy, direct_vm, direct_alice, direct_bob):
    lacuna = direct_deploy("contracts/lacuna.py")
    agreement_id, _ = _resolved_agreement(lacuna, direct_vm, direct_alice, direct_bob)
    bad = dict(PERFORMANCE_VERDICT_BASE, summary="")
    direct_vm.mock_llm(r".*", _fenced(bad))

    with pytest.raises(Exception, match="summary must be 1-"):
        lacuna.evaluate_performance(agreement_id)


def test_evaluate_performance_rejects_oversized_summary(direct_deploy, direct_vm, direct_alice, direct_bob):
    lacuna = direct_deploy("contracts/lacuna.py")
    agreement_id, _ = _resolved_agreement(lacuna, direct_vm, direct_alice, direct_bob)
    bad = dict(PERFORMANCE_VERDICT_BASE, summary="x" * 1001)
    direct_vm.mock_llm(r".*", _fenced(bad))

    with pytest.raises(Exception, match="summary must be 1-"):
        lacuna.evaluate_performance(agreement_id)


def test_evaluate_performance_cannot_run_before_resolution_frozen(direct_deploy, direct_vm, direct_alice, direct_bob):
    lacuna = direct_deploy("contracts/lacuna.py")
    agreement_id, _ = _observing_agreement(lacuna, direct_vm, direct_alice, direct_bob)
    direct_vm.sender = direct_alice
    direct_vm.mock_llm(r".*", _fenced(PERFORMANCE_VERDICT_BASE))

    with pytest.raises(Exception, match="RESOLUTION_FROZEN"):
        lacuna.evaluate_performance(agreement_id)


def test_repeated_adjudication_cannot_overwrite_proposed_verdict(direct_deploy, direct_vm, direct_alice, direct_bob):
    lacuna = direct_deploy("contracts/lacuna.py")
    agreement_id, _ = _resolved_agreement(lacuna, direct_vm, direct_alice, direct_bob)
    direct_vm.mock_llm(r".*", _fenced(PERFORMANCE_VERDICT_BASE))
    first = json.loads(lacuna.evaluate_performance(agreement_id))

    direct_vm.mock_llm(r".*", _fenced(LOW_ATTRIBUTION_VERDICT))
    with pytest.raises(Exception, match="RESOLUTION_FROZEN"):
        lacuna.evaluate_performance(agreement_id)

    agreement = json.loads(lacuna.get_agreement(agreement_id))
    assert agreement["verdict_id"] == first["verdict_id"]
    unchanged = json.loads(lacuna.get_verdict(first["verdict_id"]))
    assert unchanged["attribution_bps"] == 8200


def test_evaluate_performance_frozen_evidence_remains_immutable(direct_deploy, direct_vm, direct_alice, direct_bob):
    lacuna = direct_deploy("contracts/lacuna.py")
    agreement_id, _ = _resolved_agreement(lacuna, direct_vm, direct_alice, direct_bob)
    outcome_before = json.loads(lacuna.list_outcome_evidence(agreement_id))
    baseline_evidence_before = json.loads(lacuna.list_baseline_evidence(agreement_id))

    direct_vm.mock_llm(r".*", _fenced(PERFORMANCE_VERDICT_BASE))
    lacuna.evaluate_performance(agreement_id)

    outcome_after = json.loads(lacuna.list_outcome_evidence(agreement_id))
    baseline_evidence_after = json.loads(lacuna.list_baseline_evidence(agreement_id))
    assert outcome_after == outcome_before
    assert baseline_evidence_after == baseline_evidence_before


def test_evaluate_performance_locked_baseline_remains_immutable(direct_deploy, direct_vm, direct_alice, direct_bob):
    lacuna = direct_deploy("contracts/lacuna.py")
    agreement_id, baseline_id = _resolved_agreement(lacuna, direct_vm, direct_alice, direct_bob)
    baseline_before = json.loads(lacuna.get_counterfactual_baseline(baseline_id))

    direct_vm.mock_llm(r".*", _fenced(PERFORMANCE_VERDICT_BASE))
    lacuna.evaluate_performance(agreement_id)

    baseline_after = json.loads(lacuna.get_counterfactual_baseline(baseline_id))
    assert baseline_after == baseline_before


# =========================================================
# Deterministic settlement, appeals, finalization (Stage 8)
# =========================================================


def _proposed_verdict(
    lacuna, direct_vm, direct_alice, direct_bob,
    verdict=None, agreement_id="AGR-1", escrow_amount=10_000,
):
    agreement_id, baseline_id = _resolved_agreement(
        lacuna, direct_vm, direct_alice, direct_bob,
        agreement_id=agreement_id, escrow_amount=escrow_amount,
    )
    direct_vm.mock_llm(r".*", _fenced(verdict or PERFORMANCE_VERDICT_BASE))
    record = json.loads(lacuna.evaluate_performance(agreement_id))
    return agreement_id, baseline_id, record


def _appeal_result(decision="UPHOLD", verdict=None):
    result = dict(verdict or PERFORMANCE_VERDICT_BASE)
    result["decision"] = decision
    result["replacement_required"] = decision == "MODIFY"
    return result


@pytest.mark.parametrize(
    "performance,expected_base,status",
    [
        (0, 0, "BELOW_MINIMUM"),
        (1999, 0, "BELOW_MINIMUM"),
        (2000, 0, "PARTIAL_BASE_PAYMENT"),
        (4000, 5000, "PARTIAL_BASE_PAYMENT"),
        (6000, 10000, "FULL_BASE_PAYMENT"),
        (10000, 10000, "FULL_BASE_PAYMENT"),
    ],
)
def test_settlement_thresholds_and_boundaries(
    direct_deploy, direct_vm, direct_alice, direct_bob,
    performance, expected_base, status,
):
    lacuna = direct_deploy("contracts/lacuna.py")
    verdict = dict(
        PERFORMANCE_VERDICT_BASE,
        attribution_bps=performance,
        performance_bps=performance,
        alternative_explanation_strength_bps=0,
        reason_codes=["OUTCOME_NOT_OUTSIDE_EXPECTED_RANGE"] if performance == 0 else ["OUTCOME_EXCEEDS_EXPECTED_RANGE"],
    )
    agreement_id, _, _ = _proposed_verdict(lacuna, direct_vm, direct_alice, direct_bob, verdict)
    preview = json.loads(lacuna.get_settlement_preview(agreement_id))
    assert preview["base_payment"] == expected_base
    assert preview["final_payment"] == expected_base
    assert preview["unpaid_amount"] == 10_000 - expected_base
    assert preview["settlement_status"] == status
    assert 0 <= preview["base_payment"] <= preview["escrow_amount"]


def test_settlement_bonus_entitlement_and_cap(direct_deploy, direct_vm, direct_alice, direct_bob):
    lacuna = direct_deploy("contracts/lacuna.py")
    verdict = dict(PERFORMANCE_VERDICT_BASE, attribution_bps=10000, performance_bps=10000)
    agreement_id, _, _ = _proposed_verdict(lacuna, direct_vm, direct_alice, direct_bob, verdict)
    preview = json.loads(lacuna.get_settlement_preview(agreement_id))
    assert preview["bonus_payment"] == 1500
    assert preview["bonus_advisory_only"] is True
    assert preview["final_payment"] == 10_000


def test_settlement_unresolved_confounder_cap(direct_deploy, direct_vm, direct_alice, direct_bob):
    lacuna = direct_deploy("contracts/lacuna.py")
    verdict = dict(PERFORMANCE_VERDICT_BASE, attribution_bps=9000, performance_bps=9000, alternative_explanation_strength_bps=5000)
    agreement_id, _, _ = _proposed_verdict(lacuna, direct_vm, direct_alice, direct_bob, verdict)
    preview = json.loads(lacuna.get_settlement_preview(agreement_id))
    assert preview["confounder_cap_applied"] is True
    assert preview["effective_performance_bps"] == 3000
    assert preview["base_payment"] == 2500


def test_settlement_guardrail_cap(direct_deploy, direct_vm, direct_alice, direct_bob):
    lacuna = direct_deploy("contracts/lacuna.py")
    verdict = dict(GUARDRAIL_VIOLATION_VERDICT, attribution_bps=9000, performance_bps=8000)
    agreement_id, _, _ = _proposed_verdict(lacuna, direct_vm, direct_alice, direct_bob, verdict)
    preview = json.loads(lacuna.get_settlement_preview(agreement_id))
    assert preview["guardrail_cap_applied"] is True
    assert preview["effective_performance_bps"] == 4000
    assert preview["base_payment"] == 5000


def test_settlement_both_caps_together(direct_deploy, direct_vm, direct_alice, direct_bob):
    lacuna = direct_deploy("contracts/lacuna.py")
    verdict = dict(GUARDRAIL_VIOLATION_VERDICT, attribution_bps=9000, performance_bps=8000, alternative_explanation_strength_bps=5000)
    agreement_id, _, _ = _proposed_verdict(lacuna, direct_vm, direct_alice, direct_bob, verdict)
    preview = json.loads(lacuna.get_settlement_preview(agreement_id))
    assert preview["confounder_cap_applied"] is True
    assert preview["guardrail_cap_applied"] is True
    assert preview["effective_performance_bps"] == 3000
    assert preview["base_payment"] == 2500


def test_settlement_zero_escrow_and_repeatability(direct_deploy, direct_vm, direct_alice, direct_bob):
    lacuna = direct_deploy("contracts/lacuna.py")
    agreement_id, _, _ = _proposed_verdict(
        lacuna, direct_vm, direct_alice, direct_bob, escrow_amount=0,
    )
    first = json.loads(lacuna.get_settlement_preview(agreement_id))
    second = json.loads(lacuna.get_settlement_preview(agreement_id))
    assert first == second
    assert first["escrow_amount"] == first["base_payment"] == first["final_payment"] == 0
    assert first["bonus_payment"] == first["unpaid_amount"] == 0


def test_settlement_monotonic_for_identical_caps(direct_deploy, direct_vm, direct_alice, direct_bob):
    lacuna = direct_deploy("contracts/lacuna.py")
    agreement_id, _, verdict = _proposed_verdict(lacuna, direct_vm, direct_alice, direct_bob)
    payments = []
    for performance in (2000, 3000, 4000, 5000, 6000, 9000):
        # Direct-storage mutation is intentionally test-only: it isolates the
        # pure view's arithmetic while holding every confounder/guardrail and
        # policy input identical. No production write method permits this.
        stored = json.loads(lacuna.verdicts[verdict["verdict_id"]])
        stored["performance_bps"] = performance
        stored["attribution_bps"] = performance
        stored["alternative_explanation_strength_bps"] = 0
        stored["guardrail_penalty_bps"] = 0
        lacuna.verdicts[verdict["verdict_id"]] = json.dumps(stored)
        payments.append(json.loads(lacuna.get_settlement_preview(agreement_id))["base_payment"])
    assert payments == sorted(payments)


def test_open_appeal_valid_and_listed(direct_deploy, direct_vm, direct_alice, direct_bob):
    lacuna = direct_deploy("contracts/lacuna.py")
    agreement_id, _, verdict = _proposed_verdict(lacuna, direct_vm, direct_alice, direct_bob)
    direct_vm.sender = direct_bob
    assert lacuna.open_appeal("APP-1", agreement_id, "ATTRIBUTION_OVERSTATED", "Attribution ignores a confounder.", ["OUT-1"]) == "APP-1"
    appeal = json.loads(lacuna.get_appeal("APP-1"))
    assert appeal["verdict_id"] == verdict["verdict_id"]
    assert appeal["status"] == "OPEN"
    assert len(json.loads(lacuna.list_appeals(agreement_id))) == 1
    assert json.loads(lacuna.get_agreement(agreement_id))["status"] == "APPEALED"


@pytest.mark.parametrize("mode", ["unauthorized", "ground", "ref"])
def test_open_appeal_rejects_unauthorized_invalid_ground_and_ref(
    direct_deploy, direct_vm, direct_alice, direct_bob, direct_charlie, mode,
):
    lacuna = direct_deploy("contracts/lacuna.py")
    agreement_id, _, _ = _proposed_verdict(lacuna, direct_vm, direct_alice, direct_bob)
    direct_vm.sender = direct_charlie if mode == "unauthorized" else direct_alice
    with pytest.raises(Exception, match="client or contractor" if mode == "unauthorized" else "ground must" if mode == "ground" else "outside the frozen"):
        lacuna.open_appeal("APP-1", agreement_id, "NOT_REAL" if mode == "ground" else "EVIDENCE_OMITTED", "Statement", ["NOPE"] if mode == "ref" else ["OUT-1"])


def test_open_appeal_rejects_duplicate_unresolved(direct_deploy, direct_vm, direct_alice, direct_bob):
    lacuna = direct_deploy("contracts/lacuna.py")
    agreement_id, _, _ = _proposed_verdict(lacuna, direct_vm, direct_alice, direct_bob)
    direct_vm.sender = direct_alice
    lacuna.open_appeal("APP-1", agreement_id, "EVIDENCE_OMITTED", "One", ["OUT-1"])
    with pytest.raises(Exception, match="VERDICT_PROPOSED"):
        lacuna.open_appeal("APP-2", agreement_id, "EVIDENCE_OMITTED", "Two", ["OUT-1"])


@pytest.mark.parametrize("decision", ["UPHOLD", "MODIFY", "VOID"])
def test_evaluate_appeal_decisions(direct_deploy, direct_vm, direct_alice, direct_bob, decision):
    lacuna = direct_deploy("contracts/lacuna.py")
    agreement_id, baseline_id, original = _proposed_verdict(lacuna, direct_vm, direct_alice, direct_bob)
    baseline_before = json.loads(lacuna.get_counterfactual_baseline(baseline_id))
    evidence_before = json.loads(lacuna.list_outcome_evidence(agreement_id))
    direct_vm.sender = direct_bob
    lacuna.open_appeal("APP-1", agreement_id, "ATTRIBUTION_OVERSTATED", "Review attribution.", ["OUT-1"])
    direct_vm.clear_mocks()
    modified = dict(PERFORMANCE_VERDICT_BASE, attribution_bps=6000, performance_bps=5500, summary="Corrected attribution after appeal review.")
    direct_vm.mock_llm(r".*", _fenced(_appeal_result(decision, modified if decision == "MODIFY" else None)))
    appeal = json.loads(lacuna.evaluate_appeal("APP-1"))
    agreement = json.loads(lacuna.get_agreement(agreement_id))
    assert appeal["decision"] == decision
    assert json.loads(lacuna.get_counterfactual_baseline(baseline_id)) == baseline_before
    assert json.loads(lacuna.list_outcome_evidence(agreement_id)) == evidence_before
    original_after = json.loads(lacuna.get_verdict(original["verdict_id"]))
    if decision == "UPHOLD":
        assert agreement["status"] == "VERDICT_PROPOSED"
        assert agreement["verdict_id"] == original["verdict_id"]
        assert original_after["status"] == "PROPOSED"
    elif decision == "MODIFY":
        assert agreement["status"] == "VERDICT_PROPOSED"
        assert appeal["replacement_verdict_id"] != original["verdict_id"]
        assert original_after["status"] == "VOID"
        replacement = json.loads(lacuna.get_verdict(appeal["replacement_verdict_id"]))
        assert replacement["performance_bps"] == 5500
        assert len(json.loads(lacuna.list_verdicts(agreement_id))) == 2
    else:
        assert agreement["status"] == "RESOLUTION_FROZEN"
        assert agreement["verdict_id"] == ""
        assert original_after["status"] == "VOID"


def test_evaluate_appeal_rejects_malformed_output(direct_deploy, direct_vm, direct_alice, direct_bob):
    lacuna = direct_deploy("contracts/lacuna.py")
    agreement_id, _, _ = _proposed_verdict(lacuna, direct_vm, direct_alice, direct_bob)
    direct_vm.sender = direct_alice
    lacuna.open_appeal("APP-1", agreement_id, "EVIDENCE_OMITTED", "Review.", ["OUT-1"])
    direct_vm.clear_mocks()
    direct_vm.mock_llm(r".*", "not json")
    with pytest.raises(Exception, match="Malformed appeal output"):
        lacuna.evaluate_appeal("APP-1")


def test_finalize_verdict_and_final_state_invariants(direct_deploy, direct_vm, direct_alice, direct_bob):
    lacuna = direct_deploy("contracts/lacuna.py")
    agreement_id, baseline_id, proposed = _proposed_verdict(lacuna, direct_vm, direct_alice, direct_bob)
    baseline_before = json.loads(lacuna.get_counterfactual_baseline(baseline_id))
    evidence_before = json.loads(lacuna.list_outcome_evidence(agreement_id))
    direct_vm.sender = direct_alice
    pending = json.loads(lacuna.finalize_verdict(agreement_id))
    assert pending["status"] == "AWAITING_COUNTERPARTY_FINALIZATION"
    pending_agreement = json.loads(lacuna.get_agreement(agreement_id))
    assert pending_agreement["status"] == "VERDICT_PROPOSED"
    assert pending_agreement["client_verdict_finalization"] is True
    assert pending_agreement["contractor_verdict_finalization"] is False

    direct_vm.sender = direct_bob
    final = json.loads(lacuna.finalize_verdict(agreement_id))
    assert final["status"] == "FINAL"
    assert json.loads(lacuna.get_agreement(agreement_id))["status"] == "FINALIZED"
    assert json.loads(lacuna.get_counterfactual_baseline(baseline_id)) == baseline_before
    assert json.loads(lacuna.list_outcome_evidence(agreement_id)) == evidence_before
    assert json.loads(lacuna.get_settlement_preview(agreement_id))["performance_bps"] == proposed["performance_bps"]
    with pytest.raises(Exception, match="RESOLUTION_FROZEN"):
        lacuna.evaluate_performance(agreement_id)
    with pytest.raises(Exception, match="VERDICT_PROPOSED"):
        lacuna.finalize_verdict(agreement_id)


def test_one_party_cannot_finalize_alone_by_calling_twice(direct_deploy, direct_vm, direct_alice, direct_bob):
    lacuna = direct_deploy("contracts/lacuna.py")
    agreement_id, _, _ = _proposed_verdict(lacuna, direct_vm, direct_alice, direct_bob)
    direct_vm.sender = direct_bob

    for _ in range(2):
        pending = json.loads(lacuna.finalize_verdict(agreement_id))
        assert pending["status"] == "AWAITING_COUNTERPARTY_FINALIZATION"

    agreement = json.loads(lacuna.get_agreement(agreement_id))
    assert agreement["status"] == "VERDICT_PROPOSED"
    assert agreement["client_verdict_finalization"] is False
    assert agreement["contractor_verdict_finalization"] is True
    # The counterparty's appeal window is still open.
    direct_vm.sender = direct_alice
    lacuna.open_appeal("APP-1", agreement_id, "ATTRIBUTION_OVERSTATED", "Review attribution.", ["OUT-1"])
    assert json.loads(lacuna.get_agreement(agreement_id))["status"] == "APPEALED"


def test_resolved_appeal_clears_earlier_finalization_acknowledgement(
    direct_deploy, direct_vm, direct_alice, direct_bob
):
    lacuna = direct_deploy("contracts/lacuna.py")
    agreement_id, _, _ = _proposed_verdict(lacuna, direct_vm, direct_alice, direct_bob)
    direct_vm.sender = direct_alice
    lacuna.finalize_verdict(agreement_id)

    direct_vm.sender = direct_bob
    lacuna.open_appeal("APP-1", agreement_id, "ATTRIBUTION_OVERSTATED", "Review attribution.", ["OUT-1"])
    direct_vm.clear_mocks()
    direct_vm.mock_llm(r".*", _fenced(_appeal_result("UPHOLD")))
    lacuna.evaluate_appeal("APP-1")

    agreement = json.loads(lacuna.get_agreement(agreement_id))
    assert agreement["status"] == "VERDICT_PROPOSED"
    assert agreement["client_verdict_finalization"] is False
    assert agreement["contractor_verdict_finalization"] is False

    # The pre-appeal acknowledgement no longer counts: both parties must
    # acknowledge the verdict that survived the appeal.
    pending = json.loads(lacuna.finalize_verdict(agreement_id))
    assert pending["status"] == "AWAITING_COUNTERPARTY_FINALIZATION"
    direct_vm.sender = direct_alice
    assert json.loads(lacuna.finalize_verdict(agreement_id))["status"] == "FINAL"
    assert json.loads(lacuna.get_agreement(agreement_id))["status"] == "FINALIZED"


def _warp_relative_to_appeal_window(lacuna, direct_vm, agreement_id, seconds):
    """Move the VM clock to the current appeal-window deadline +/- seconds."""
    deadline = json.loads(lacuna.get_agreement(agreement_id))["appeal_window_ends_at"]
    assert deadline
    direct_vm.warp((datetime.fromisoformat(deadline) + timedelta(seconds=seconds)).isoformat())
    return deadline


def test_appeal_window_closes_before_single_party_can_finalize(
    direct_deploy, direct_vm, direct_alice, direct_bob
):
    lacuna = direct_deploy("contracts/lacuna.py")
    agreement_id, _, _ = _proposed_verdict(lacuna, direct_vm, direct_alice, direct_bob)
    direct_vm.sender = direct_bob

    # One second before the window closes, the counterparty's acknowledgement
    # is still required.
    _warp_relative_to_appeal_window(lacuna, direct_vm, agreement_id, -1)
    pending = json.loads(lacuna.finalize_verdict(agreement_id))
    assert pending["status"] == "AWAITING_COUNTERPARTY_FINALIZATION"
    assert pending["appeal_window_ends_at"]
    assert json.loads(lacuna.get_agreement(agreement_id))["status"] == "VERDICT_PROPOSED"

    # Once it closes with no appeal opened, settlement is no longer hostage to
    # a counterparty that never responds.
    _warp_relative_to_appeal_window(lacuna, direct_vm, agreement_id, 1)
    final = json.loads(lacuna.finalize_verdict(agreement_id))
    assert final["status"] == "FINAL"
    assert json.loads(lacuna.get_agreement(agreement_id))["status"] == "FINALIZED"


def test_resolved_appeal_restarts_the_appeal_window(
    direct_deploy, direct_vm, direct_alice, direct_bob
):
    lacuna = direct_deploy("contracts/lacuna.py")
    agreement_id, _, _ = _proposed_verdict(lacuna, direct_vm, direct_alice, direct_bob)
    direct_vm.sender = direct_bob
    first_deadline = _warp_relative_to_appeal_window(lacuna, direct_vm, agreement_id, -1)

    lacuna.open_appeal("APP-1", agreement_id, "ATTRIBUTION_OVERSTATED", "Review attribution.", ["OUT-1"])
    direct_vm.clear_mocks()
    direct_vm.mock_llm(r".*", _fenced(_appeal_result("UPHOLD")))
    lacuna.evaluate_appeal("APP-1")

    agreement = json.loads(lacuna.get_agreement(agreement_id))
    assert datetime.fromisoformat(agreement["appeal_window_ends_at"]) > datetime.fromisoformat(first_deadline)
    # The expired first window cannot be reused to close the upheld verdict.
    assert json.loads(lacuna.finalize_verdict(agreement_id))["status"] == "AWAITING_COUNTERPARTY_FINALIZATION"


def test_voided_verdict_clears_the_appeal_window(direct_deploy, direct_vm, direct_alice, direct_bob):
    lacuna = direct_deploy("contracts/lacuna.py")
    agreement_id, _, _ = _proposed_verdict(lacuna, direct_vm, direct_alice, direct_bob)
    direct_vm.sender = direct_alice
    lacuna.open_appeal("APP-1", agreement_id, "ATTRIBUTION_OVERSTATED", "Review attribution.", ["OUT-1"])
    direct_vm.clear_mocks()
    direct_vm.mock_llm(r".*", _fenced(_appeal_result("VOID")))
    lacuna.evaluate_appeal("APP-1")

    agreement = json.loads(lacuna.get_agreement(agreement_id))
    assert agreement["status"] == "RESOLUTION_FROZEN"
    assert agreement["appeal_window_ends_at"] == ""


def test_finalize_blocked_by_unresolved_appeal_and_void_verdict(direct_deploy, direct_vm, direct_alice, direct_bob):
    lacuna = direct_deploy("contracts/lacuna.py")
    agreement_id, _, _ = _proposed_verdict(lacuna, direct_vm, direct_alice, direct_bob)
    direct_vm.sender = direct_alice
    lacuna.open_appeal("APP-1", agreement_id, "EVIDENCE_OMITTED", "Review.", ["OUT-1"])
    with pytest.raises(Exception, match="VERDICT_PROPOSED"):
        lacuna.finalize_verdict(agreement_id)
    direct_vm.clear_mocks()
    direct_vm.mock_llm(r".*", _fenced(_appeal_result("VOID")))
    lacuna.evaluate_appeal("APP-1")
    with pytest.raises(Exception, match="VERDICT_PROPOSED"):
        lacuna.finalize_verdict(agreement_id)


def test_finalize_verdict_rejects_unauthorized_party(
    direct_deploy, direct_vm, direct_alice, direct_bob, direct_charlie,
):
    lacuna = direct_deploy("contracts/lacuna.py")
    agreement_id, _, _ = _proposed_verdict(lacuna, direct_vm, direct_alice, direct_bob)
    direct_vm.sender = direct_charlie
    with pytest.raises(Exception, match="client or contractor"):
        lacuna.finalize_verdict(agreement_id)


def test_baseline_challenge_rejects_extra_unknown_fields(
    direct_deploy, direct_vm, direct_alice, direct_bob,
):
    lacuna = direct_deploy("contracts/lacuna.py")
    agreement_id, _ = _proposed_agreement(lacuna, direct_vm, direct_alice, direct_bob)
    direct_vm.sender = direct_alice
    lacuna.open_baseline_challenge("CH-strict", agreement_id, "EVIDENCE_OMITTED", "Review.", ["EV-1"])
    direct_vm.mock_llm(r".*", _fenced(dict(UPHOLD_VERDICT, unexpected_field=True)))
    with pytest.raises(Exception, match="unsupported field"):
        lacuna.evaluate_baseline_challenge("CH-strict")


def test_performance_rejects_extra_unknown_fields(
    direct_deploy, direct_vm, direct_alice, direct_bob,
):
    lacuna = direct_deploy("contracts/lacuna.py")
    agreement_id, _ = _resolved_agreement(lacuna, direct_vm, direct_alice, direct_bob)
    direct_vm.mock_llm(r".*", _fenced(dict(PERFORMANCE_VERDICT_BASE, unexpected_field=True)))
    with pytest.raises(Exception, match="unsupported field"):
        lacuna.evaluate_performance(agreement_id)


def test_performance_appeal_rejects_extra_unknown_fields(
    direct_deploy, direct_vm, direct_alice, direct_bob,
):
    lacuna = direct_deploy("contracts/lacuna.py")
    agreement_id, _, _ = _proposed_verdict(lacuna, direct_vm, direct_alice, direct_bob)
    direct_vm.sender = direct_alice
    lacuna.open_appeal("APP-strict", agreement_id, "EVIDENCE_OMITTED", "Review.", ["OUT-1"])
    direct_vm.clear_mocks()
    strict_bad = dict(_appeal_result("UPHOLD"), unexpected_field=True)
    direct_vm.mock_llm(r".*", _fenced(strict_bad))
    with pytest.raises(Exception, match="unsupported field"):
        lacuna.evaluate_appeal("APP-strict")


def test_source_independence_ignores_port_variation(
    direct_deploy, direct_vm, direct_alice, direct_bob,
):
    lacuna = direct_deploy("contracts/lacuna.py")
    agreement_id, *_ = setup_agreement(lacuna, direct_vm, direct_alice, direct_bob)
    direct_vm.sender = direct_alice
    submit_evidence(
        lacuna,
        agreement_id=agreement_id,
        evidence_id="EV-port-1",
        source_type="PUBLIC_ANALYTICS",
        source_url="https://same.example.com:443/analytics",
    )
    submit_evidence(
        lacuna,
        agreement_id=agreement_id,
        evidence_id="EV-port-2",
        source_type="COMMUNITY_ACTIVITY",
        source_url="https://same.example.com:8443/community",
    )
    evidence = json.loads(lacuna.list_baseline_evidence(agreement_id))
    assert {record["source_host"] for record in evidence} == {"same.example.com"}
    with pytest.raises(Exception, match="Insufficient independent sources"):
        lacuna.freeze_baseline_evidence(agreement_id)
