# { "Depends": "py-genlayer:1jb45aa8ynh2a9c9xn3b7qqh8sm5q93hwfp7jqmwsfhh8jpz09h6" }

from genlayer import *

import json

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


class Lacuna(gl.Contract):
    # PerformanceAgreement
    agreements: TreeMap[str, str]
    agreement_count: u256

    # BaselineConstitution
    constitutions: TreeMap[str, str]
    constitution_count: u256

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

    # SettlementPolicy
    settlement_policies: TreeMap[str, str]
    settlement_policy_count: u256

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

    # --- Stage 1 proof-of-storage methods only. Full lifecycle is Stage 2+. ---

    @gl.public.write
    def create_agreement(
        self,
        agreement_id: str,
        client: str,
        contractor: str,
        title: str,
        obligation: str,
    ) -> str:
        if agreement_id in self.agreements:
            raise gl.vm.UserError("Agreement ID already exists")
        if not title or len(title) > 200:
            raise gl.vm.UserError("Title must be 1-200 characters")
        if not obligation or len(obligation) > 2000:
            raise gl.vm.UserError("Obligation must be 1-2000 characters")

        record = {
            "agreement_id": agreement_id,
            "client": client,
            "contractor": contractor,
            "title": title,
            "obligation": obligation,
            "constitution_id": "",
            "settlement_policy_id": "",
            "baseline_window_start": "",
            "baseline_window_end": "",
            "observation_window_start": "",
            "observation_window_end": "",
            "status": "DRAFT",
            "escrow_amount": "0",
            "baseline_id": "",
            "verdict_id": "",
            "appeal_id": "",
            "created_by": gl.message.sender_address.as_hex,
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
