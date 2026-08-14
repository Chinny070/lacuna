import type { TransactionHash, TransactionState, TransactionUpdate } from "./transactions";
import { createWalletClient, LACUNA_CONTRACT_ADDRESS } from "./client";
import { normalizeGenLayerError } from "./errors";
import { requireSchemaMethod, type ContractValue } from "./schema";
import { waitForFinality } from "./transactions";

export type WalletWriteContext = { account: `0x${string}`; provider: NonNullable<Window["ethereum"]> };

async function write(context: WalletWriteContext, method: string, args: ContractValue[], update: TransactionUpdate): Promise<TransactionState> {
  requireSchemaMethod(method, false);
  update({ phase: "awaiting_signature" });
  try {
    const client = createWalletClient(context.account, context.provider);
    const hash = await client.writeContract({ address: LACUNA_CONTRACT_ADDRESS, functionName: method, args, value: 0n }) as TransactionHash;
    await waitForFinality(client, hash, update);
    return { phase: "finalized_success", hash };
  } catch (error) {
    const normalized = normalizeGenLayerError(error);
    update({ phase: normalized.code === "user_rejected" ? "rejected" : normalized.code === "timeout" ? "timeout" : "finalized_execution_failed", error: normalized });
    throw normalized;
  }
}

export const lacunaWrite = {
  acceptBaseline: (c: WalletWriteContext, u: TransactionUpdate, agreementId: string) => write(c, "accept_baseline", [agreementId], u),
  createAgreement: (c: WalletWriteContext, u: TransactionUpdate, ...a: [string, string, string, string, string, string, string, number, number, number, number, number]) => write(c, "create_agreement", a, u),
  createBaselineConstitution: (c: WalletWriteContext, u: TransactionUpdate, ...a: [string, string, string[], string[], string, string[], number, string, string[], string[]]) => write(c, "create_baseline_constitution", a, u),
  createSettlementPolicy: (c: WalletWriteContext, u: TransactionUpdate, ...a: [string, number, number, number, number, number, number]) => write(c, "create_settlement_policy", a, u),
  evaluateAppeal: (c: WalletWriteContext, u: TransactionUpdate, appealId: string) => write(c, "evaluate_appeal", [appealId], u),
  evaluateBaseline: (c: WalletWriteContext, u: TransactionUpdate, agreementId: string) => write(c, "evaluate_baseline", [agreementId], u),
  evaluateBaselineChallenge: (c: WalletWriteContext, u: TransactionUpdate, challengeId: string) => write(c, "evaluate_baseline_challenge", [challengeId], u),
  evaluatePerformance: (c: WalletWriteContext, u: TransactionUpdate, agreementId: string) => write(c, "evaluate_performance", [agreementId], u),
  finalizeVerdict: (c: WalletWriteContext, u: TransactionUpdate, agreementId: string) => write(c, "finalize_verdict", [agreementId], u),
  freezeBaselineEvidence: (c: WalletWriteContext, u: TransactionUpdate, agreementId: string) => write(c, "freeze_baseline_evidence", [agreementId], u),
  freezeResolution: (c: WalletWriteContext, u: TransactionUpdate, agreementId: string) => write(c, "freeze_resolution", [agreementId], u),
  openAppeal: (c: WalletWriteContext, u: TransactionUpdate, ...a: [string, string, string, string, string[]]) => write(c, "open_appeal", a, u),
  openBaselineChallenge: (c: WalletWriteContext, u: TransactionUpdate, ...a: [string, string, string, string, string[]]) => write(c, "open_baseline_challenge", a, u),
  startObservation: (c: WalletWriteContext, u: TransactionUpdate, agreementId: string) => write(c, "start_observation", [agreementId], u),
  submitAlternativeExplanation: (c: WalletWriteContext, u: TransactionUpdate, ...a: [string, string, string, string, string[], string[], string, number]) => write(c, "submit_alternative_explanation", a, u),
  submitBaselineEvidence: (c: WalletWriteContext, u: TransactionUpdate, ...a: [string, string, string, string, string, string, string, number, number]) => write(c, "submit_baseline_evidence", a, u),
  submitOutcomeEvidence: (c: WalletWriteContext, u: TransactionUpdate, ...a: [string, string, string, string, string, string, string, number, number, number]) => write(c, "submit_outcome_evidence", a, u),
} as const;
