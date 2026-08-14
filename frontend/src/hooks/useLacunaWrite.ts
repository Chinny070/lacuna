import { useState } from "react";
import { useInjectedWallet } from "./useInjectedWallet";
import { type NormalizedError } from "../lib/genlayer/errors";
import { type ContractValue } from "../lib/genlayer/schema";
import { type TransactionState } from "../lib/genlayer/transactions";
import { lacunaWrite, type WalletWriteContext } from "../lib/genlayer/write";

export type WriteKey = keyof typeof lacunaWrite;
type UnsafeWriter = (context: WalletWriteContext, update: (state: TransactionState) => void, ...args: ContractValue[]) => Promise<TransactionState>;

export function useLacunaWrite() {
  const wallet = useInjectedWallet();
  const [transaction, setTransaction] = useState<TransactionState>({ phase: "idle" });
  const [error, setError] = useState<NormalizedError>();
  const submit = async (key: WriteKey, args: ContractValue[]) => {
    setError(undefined);
    if (!wallet.available || !window.ethereum) { setTransaction({ phase: "wallet_required" }); return; }
    if (!wallet.account) { setTransaction({ phase: "wallet_required" }); await wallet.connect(); return; }
    if (!wallet.isStudioNet) { setTransaction({ phase: "wrong_network" }); return; }
    try {
      const writer = lacunaWrite[key] as unknown as UnsafeWriter;
      await writer({ account: wallet.account, provider: window.ethereum }, setTransaction, ...args);
    } catch (cause) { setError(cause as NormalizedError); }
  };
  return { wallet, transaction, error, submit };
}
