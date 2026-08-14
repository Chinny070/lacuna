import type { TransactionState } from "../lib/genlayer/transactions";

export function TransactionStatus({ state }: { state: TransactionState }) {
  if (state.phase === "idle") return <p className="muted">No transaction has been started.</p>;
  return (
    <section className="transaction" aria-live="polite">
      <strong>Transaction: {state.phase.replaceAll("_", " ")}</strong>
      {state.hash && <code>{state.hash}</code>}
      {state.error && <p className="error">{state.error.message}</p>}
      {state.error?.detail && <details><summary>Developer detail</summary><pre>{state.error.detail}</pre></details>}
    </section>
  );
}
