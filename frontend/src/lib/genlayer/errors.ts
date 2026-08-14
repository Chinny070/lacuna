export type NormalizedErrorCode =
  | "wallet_unavailable"
  | "user_rejected"
  | "wrong_network"
  | "contract_revert"
  | "rpc_failure"
  | "execution_failed"
  | "timeout"
  | "record_not_found"
  | "unknown";

export type NormalizedError = { code: NormalizedErrorCode; message: string; detail?: string };

export function isNormalizedError(error: unknown): error is NormalizedError {
  return typeof error === "object" && error !== null && "code" in error && "message" in error;
}

export function normalizeGenLayerError(error: unknown): NormalizedError {
  const detail = error instanceof Error ? error.message : String(error);
  const lower = detail.toLowerCase();
  if (lower.includes("user rejected") || lower.includes("4001")) return { code: "user_rejected", message: "Wallet signature was rejected.", detail };
  if (lower.includes("wallet") && (lower.includes("not found") || lower.includes("unavailable"))) return { code: "wallet_unavailable", message: "No injected wallet is available.", detail };
  if (lower.includes("chain") || lower.includes("network")) return { code: "wrong_network", message: "Switch your wallet to GenLayer StudioNet.", detail };
  if (lower.includes("timed out") || lower.includes("timeout")) return { code: "timeout", message: "The transaction did not finalize before the timeout.", detail };
  if (lower.includes("not found") || lower.includes("does not exist") || lower.includes("missing or invalid parameters")) return { code: "record_not_found", message: "The requested LACUNA record does not exist.", detail };
  if (lower.includes("execution") && (lower.includes("failed") || lower.includes("error"))) return { code: "execution_failed", message: "The transaction finalized with an execution failure.", detail };
  if (lower.includes("revert") || lower.includes("usererror") || lower.includes("execution failed")) return { code: "contract_revert", message: "The LACUNA contract rejected this request.", detail };
  if (lower.includes("rpc") || lower.includes("fetch") || lower.includes("network") || lower.includes("http")) return { code: "rpc_failure", message: "StudioNet could not be reached. Please retry.", detail };
  return { code: "unknown", message: "An unexpected GenLayer error occurred.", detail };
}
