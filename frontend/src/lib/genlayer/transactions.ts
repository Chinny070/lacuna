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
    if (receipt.txExecutionResultName === "FINISHED_WITH_RETURN") {
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
