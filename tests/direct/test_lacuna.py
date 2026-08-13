import hashlib
import json

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


def setup_agreement(lacuna, direct_vm, direct_alice, direct_bob, agreement_id="AGR-1"):
    """Deploys as default sender, wires client=alice, contractor=bob."""
    client = as_hex(direct_alice)
    contractor = as_hex(direct_bob)
    agreement_id, constitution_id, policy_id = create_agreement(
        lacuna, agreement_id=agreement_id, client=client, contractor=contractor
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


def test_freeze_baseline_evidence_succeeds(direct_deploy, direct_vm, direct_alice, direct_bob):
    lacuna = direct_deploy("contracts/lacuna.py")
    agreement_id, *_ = setup_agreement(lacuna, direct_vm, direct_alice, direct_bob)
    direct_vm.sender = direct_alice
    _submit_two_valid_categories(lacuna, agreement_id)

    result = lacuna.freeze_baseline_evidence(agreement_id)
    assert result == agreement_id

    agreement = json.loads(lacuna.get_agreement(agreement_id))
    assert agreement["status"] == "BASELINE_FROZEN"

    listed = json.loads(lacuna.list_baseline_evidence(agreement_id))
    assert len(listed) == 2
    assert all(item["status"] == "FROZEN" for item in listed)


def test_freeze_baseline_evidence_rejects_before_any_evidence(direct_deploy, direct_vm, direct_alice, direct_bob):
    lacuna = direct_deploy("contracts/lacuna.py")
    agreement_id, *_ = setup_agreement(lacuna, direct_vm, direct_alice, direct_bob)

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
    lacuna.freeze_baseline_evidence(agreement_id)

    with pytest.raises(Exception, match="DRAFT or BASELINE_OPEN"):
        submit_evidence(lacuna, agreement_id=agreement_id, evidence_id="EV-3")


def test_frozen_evidence_remains_queryable_and_immutable(direct_deploy, direct_vm, direct_alice, direct_bob):
    lacuna = direct_deploy("contracts/lacuna.py")
    agreement_id, *_ = setup_agreement(lacuna, direct_vm, direct_alice, direct_bob)
    direct_vm.sender = direct_alice
    _submit_two_valid_categories(lacuna, agreement_id)
    lacuna.freeze_baseline_evidence(agreement_id)

    record = json.loads(lacuna.get_baseline_evidence("EV-1"))
    assert record["status"] == "FROZEN"
    assert record["summary"] == "Historical churn dashboard export for the baseline window."
    assert record["metric_ref"] == "monthly_churn_bps"

    listed = json.loads(lacuna.list_baseline_evidence(agreement_id))
    assert {item["evidence_id"] for item in listed} == {"EV-1", "EV-2"}
