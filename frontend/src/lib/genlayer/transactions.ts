import type { createWalletClient } from "./client";
import { normalizeGenLayerError, type NormalizedError } from "./errors";

type WalletClient = ReturnType<typeof createWalletClient>;
export type TransactionHash = Parameters<WalletClient["getTransaction"]>[0]["hash"];
export type GenLayerTransaction = Awaited<ReturnType<WalletClient["getTransaction"]>>;
type ReceiptStatus = NonNullable<Parameters<WalletClient["waitForTransactionReceipt"]>[0]["status"]>;
const acceptedStatus = "ACCEPTED" as ReceiptStatus;
const finalizedStatus = "FINALIZED" as ReceiptStatus;

export type TransactionPhase =
  | "idle" | "wallet_required" | "wrong_network" | "awaiting_signature" | "submitted" | "pending"
  | "accepted" | "awaiting_finality" | "finalized_success" | "finalized_execution_failed" | "rejected" | "timeout";
export type TransactionState = { phase: TransactionPhase; hash?: TransactionHash; receipt?: GenLayerTransaction; error?: NormalizedError };
export type TransactionUpdate = (state: TransactionState) => void;

/**
 * StudioNet receipts can expose execution success at the transaction level or
 * within the consensus leader receipt. A finalized/accepted consensus status
 * alone is never considered successful execution.
 */
export function hasSuccessfulExecution(receipt: GenLayerTransaction): boolean {
  const raw = receipt as unknown as {
    txExecutionResult?: number;
    txExecutionResultName?: string;
    consensus_data?: { leader_receipt?: Array<{ execution_result?: string | number; genvm_result?: string | number }> };
  };
  if (raw.txExecutionResult === 1 || raw.txExecutionResultName === "FINISHED_WITH_RETURN") return true;

  return (raw.consensus_data?.leader_receipt ?? []).some((leaderReceipt) =>
    leaderReceipt.execution_result === "FINISHED_WITH_RETURN"
    || leaderReceipt.execution_result === "SUCCESS"
    || leaderReceipt.genvm_result === "SUCCESS",
  );
}

export async function waitForFinality(
  client: WalletClient,
  hash: TransactionHash,
  update: TransactionUpdate,
): Promise<GenLayerTransaction> {
  update({ phase: "submitted", hash });
  try {
    update({ phase: "pending", hash });
    await client.waitForTransactionReceipt({ hash, status: acceptedStatus, interval: 2_000, retries: 90 });
    update({ phase: "accepted", hash });
    update({ phase: "awaiting_finality", hash });
    const receipt = await client.waitForTransactionReceipt({ hash, status: finalizedStatus, interval: 2_000, retries: 180 });
    if (hasSuccessfulExecution(receipt)) {
      update({ phase: "finalized_success", hash, receipt });
      return receipt;
    }
    update({ phase: "finalized_execution_failed", hash, receipt, error: { code: "execution_failed", message: "The transaction finalized without a successful contract execution." } });
    throw new Error("GenLayer transaction finalized without FINISHED_WITH_RETURN.");
  } catch (error) {
    const normalized = normalizeGenLayerError(error);
    update({ phase: normalized.code === "timeout" ? "timeout" : "finalized_execution_failed", hash, error: normalized });
    throw normalized;
  }
}
