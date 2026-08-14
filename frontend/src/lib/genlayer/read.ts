import { LACUNA_CONTRACT_ADDRESS, readClient } from "./client";
import { normalizeGenLayerError } from "./errors";
import { requireSchemaMethod, type ContractValue } from "./schema";

async function read(method: string, args: ContractValue[] = []): Promise<string> {
  requireSchemaMethod(method, true);
  try {
    return String(await readClient.readContract({ address: LACUNA_CONTRACT_ADDRESS, functionName: method, args }));
  } catch (error) {
    // StudioNet returns a generic gen_call execution failure for missing
    // records. Getter calls are ID lookups, so expose the documented user
    // outcome instead of an opaque SDK error.
    if (method.startsWith("get_")) {
      throw new Error("The requested LACUNA record does not exist.");
    }
    throw normalizeGenLayerError(error);
  }
}

export const lacunaRead = {
  getAgreement: (agreementId: string) => read("get_agreement", [agreementId]),
  getAlternativeExplanation: (explanationId: string) => read("get_alternative_explanation", [explanationId]),
  getAppeal: (appealId: string) => read("get_appeal", [appealId]),
  getBaselineChallenge: (challengeId: string) => read("get_baseline_challenge", [challengeId]),
  getBaselineConstitution: (constitutionId: string) => read("get_baseline_constitution", [constitutionId]),
  getBaselineEvidence: (evidenceId: string) => read("get_baseline_evidence", [evidenceId]),
  getConstitutionVersions: (name: string) => read("get_constitution_versions", [name]),
  getCounterfactualBaseline: (baselineId: string) => read("get_counterfactual_baseline", [baselineId]),
  getOutcomeEvidence: (evidenceId: string) => read("get_outcome_evidence", [evidenceId]),
  getSettlementPolicy: (policyId: string) => read("get_settlement_policy", [policyId]),
  getSettlementPolicyVersions: (name: string) => read("get_settlement_policy_versions", [name]),
  getSettlementPreview: (agreementId: string) => read("get_settlement_preview", [agreementId]),
  getVerdict: (verdictId: string) => read("get_verdict", [verdictId]),
  listAgreements: () => read("list_agreements"),
  listAppeals: (agreementId: string) => read("list_appeals", [agreementId]),
  listBaselineChallenges: (baselineId: string) => read("list_baseline_challenges", [baselineId]),
  listBaselineEvaluations: (agreementId: string) => read("list_baseline_evaluations", [agreementId]),
  listBaselineEvidence: (agreementId: string) => read("list_baseline_evidence", [agreementId]),
  listConstitutions: () => read("list_constitutions"),
  listExplanations: (agreementId: string) => read("list_explanations", [agreementId]),
  listOutcomeEvidence: (agreementId: string) => read("list_outcome_evidence", [agreementId]),
  listSettlementPolicies: () => read("list_settlement_policies"),
  listVerdicts: (agreementId: string) => read("list_verdicts", [agreementId]),
} as const;

export async function readFreshDeploymentStatus() {
  const [agreements, constitutions, settlementPolicies] = await Promise.all([
    lacunaRead.listAgreements(),
    lacunaRead.listConstitutions(),
    lacunaRead.listSettlementPolicies(),
  ]);
  return { agreements, constitutions, settlementPolicies };
}
