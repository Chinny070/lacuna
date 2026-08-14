import { useEffect, useState } from "react";
import { TransactionStatus } from "./components/TransactionStatus";
import { useInjectedWallet } from "./hooks/useInjectedWallet";
import { GENLAYER_RPC_URL, LACUNA_CONTRACT_ADDRESS, STUDIO_NET_CHAIN_ID } from "./lib/genlayer/config";
import { normalizeGenLayerError, type NormalizedError } from "./lib/genlayer/errors";
import { readFreshDeploymentStatus } from "./lib/genlayer/read";
import { deployedContractSchema, viewMethods, writeMethods } from "./lib/genlayer/schema";
import type { TransactionState } from "./lib/genlayer/transactions";

type LiveReads = { agreements: string; constitutions: string; settlementPolicies: string };

export default function App() {
  const wallet = useInjectedWallet();
  const [reads, setReads] = useState<LiveReads>();
  const [readError, setReadError] = useState<NormalizedError>();
  const [transaction] = useState<TransactionState>({ phase: "idle" });

  useEffect(() => {
    void readFreshDeploymentStatus()
      .then(setReads)
      .catch((error: unknown) => setReadError(normalizeGenLayerError(error)));
  }, []);

  return (
    <main>
      <header>
        <p className="eyebrow">LACUNA · Stage 11 foundation</p>
        <h1>Counterfactual performance, safely connected.</h1>
        <p>Minimal StudioNet integration only. No product workflows or automatic writes are enabled here.</p>
      </header>

      <section className="card">
        <h2>Deployed contract</h2>
        <code>{LACUNA_CONTRACT_ADDRESS}</code>
        <p>StudioNet chain {STUDIO_NET_CHAIN_ID} · {GENLAYER_RPC_URL}</p>
        <p>{deployedContractSchema.method_count} audited methods: {viewMethods.length} reads / {writeMethods.length} writes.</p>
      </section>

      <section className="card">
        <h2>Wallet</h2>
        {!wallet.available && <p className="error">No injected wallet detected. Read-only StudioNet access remains available.</p>}
        {wallet.account ? <p>Connected: <code>{wallet.account}</code></p> : <button onClick={() => void wallet.connect()}>Connect wallet</button>}
        {wallet.account && !wallet.isStudioNet && <button onClick={() => void wallet.switchToStudioNet()}>Switch to StudioNet</button>}
        {wallet.account && wallet.isStudioNet && <p className="success">StudioNet connected.</p>}
        {wallet.error && <p className="error">{wallet.error.message}</p>}
      </section>

      <section className="card">
        <h2>Live protocol reads</h2>
        {reads ? <dl>
          <dt>Agreements</dt><dd><code>{reads.agreements}</code></dd>
          <dt>Constitutions</dt><dd><code>{reads.constitutions}</code></dd>
          <dt>Settlement policies</dt><dd><code>{reads.settlementPolicies}</code></dd>
        </dl> : <p className="muted">Loading StudioNet state…</p>}
        {readError && <><p className="error">{readError.message}</p><details><summary>Developer detail</summary><pre>{readError.detail}</pre></details></>}
      </section>

      <section className="card">
        <h2>Transaction finality</h2>
        <TransactionStatus state={transaction} />
        <p className="muted">A submitted hash and accepted consensus are not success. The adapter reports success only after a finalized receipt with FINISHED_WITH_RETURN.</p>
      </section>
    </main>
  );
}
