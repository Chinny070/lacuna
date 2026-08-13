import json


def test_deploy_and_initial_storage_is_empty(direct_deploy):
    lacuna = direct_deploy("contracts/lacuna.py")
    assert lacuna.agreement_count == 0
    assert lacuna.constitution_count == 0
    assert lacuna.baseline_count == 0
    assert lacuna.verdict_count == 0
    assert lacuna.settlement_policy_count == 0
    assert lacuna.appeal_count == 0
    assert json.loads(lacuna.list_agreements()) == []


def test_create_agreement_and_read_back(direct_deploy):
    lacuna = direct_deploy("contracts/lacuna.py")

    agreement_id = lacuna.create_agreement(
        "AGR-1",
        "0xclient",
        "0xcontractor",
        "Maintain community stability",
        "Keep churn and disputes low for six months.",
    )
    assert agreement_id == "AGR-1"
    assert lacuna.agreement_count == 1

    record = json.loads(lacuna.get_agreement("AGR-1"))
    assert record["agreement_id"] == "AGR-1"
    assert record["status"] == "DRAFT"
    assert record["title"] == "Maintain community stability"

    listed = json.loads(lacuna.list_agreements())
    assert len(listed) == 1
    assert listed[0]["agreement_id"] == "AGR-1"


def test_create_agreement_rejects_duplicate_id(direct_deploy):
    lacuna = direct_deploy("contracts/lacuna.py")
    lacuna.create_agreement("AGR-1", "0xclient", "0xcontractor", "Title", "Obligation")

    try:
        lacuna.create_agreement("AGR-1", "0xclient", "0xcontractor", "Title", "Obligation")
        assert False, "expected UserError for duplicate agreement id"
    except Exception as exc:
        assert "already exists" in str(exc)


def test_get_agreement_missing_raises(direct_deploy):
    lacuna = direct_deploy("contracts/lacuna.py")
    try:
        lacuna.get_agreement("does-not-exist")
        assert False, "expected UserError for missing agreement"
    except Exception as exc:
        assert "not found" in str(exc)


def test_list_agreements_returns_all_stored_ids(direct_deploy):
    lacuna = direct_deploy("contracts/lacuna.py")
    lacuna.create_agreement("AGR-1", "0xclient", "0xcontractor", "Title 1", "Obligation 1")
    lacuna.create_agreement("AGR-2", "0xclient", "0xcontractor", "Title 2", "Obligation 2")

    assert lacuna.agreement_count == 2
    listed_ids = {row["agreement_id"] for row in json.loads(lacuna.list_agreements())}
    assert listed_ids == {"AGR-1", "AGR-2"}
