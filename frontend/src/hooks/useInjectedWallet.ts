import { useCallback, useEffect, useState } from "react";
import { STUDIO_NET_CHAIN_ID, studioNetWalletChain } from "../lib/genlayer/config";
import { normalizeGenLayerError, type NormalizedError } from "../lib/genlayer/errors";

export type WalletState = {
  available: boolean;
  account?: `0x${string}`;
  chainId?: number;
  error?: NormalizedError;
};

const asChainId = (chainId: unknown): number | undefined => {
  if (typeof chainId !== "string") return undefined;
  const value = Number.parseInt(chainId, 16);
  return Number.isInteger(value) ? value : undefined;
};

export function useInjectedWallet() {
  const [wallet, setWallet] = useState<WalletState>({ available: typeof window !== "undefined" && Boolean(window.ethereum) });

  const refresh = useCallback(async () => {
    const provider = window.ethereum;
    if (!provider) return setWallet({ available: false });
    try {
      const [accounts, chainId] = await Promise.all([
        provider.request({ method: "eth_accounts" }) as Promise<string[]>,
        provider.request({ method: "eth_chainId" }),
      ]);
      setWallet({ available: true, account: accounts[0] as `0x${string}` | undefined, chainId: asChainId(chainId) });
    } catch (error) {
      setWallet({ available: true, error: normalizeGenLayerError(error) });
    }
  }, []);

  useEffect(() => {
    void refresh();
    const provider = window.ethereum;
    if (!provider) return undefined;
    const accountsChanged = (accounts: unknown) => {
      const first = Array.isArray(accounts) && typeof accounts[0] === "string" ? accounts[0] as `0x${string}` : undefined;
      setWallet((previous) => ({ ...previous, account: first }));
    };
    const chainChanged = (chain: unknown) => setWallet((previous) => ({ ...previous, chainId: asChainId(chain) }));
    const disconnected = () => setWallet({ available: true });
    provider.on("accountsChanged", accountsChanged);
    provider.on("chainChanged", chainChanged);
    provider.on("disconnect", disconnected);
    return () => {
      provider.removeListener("accountsChanged", accountsChanged);
      provider.removeListener("chainChanged", chainChanged);
      provider.removeListener("disconnect", disconnected);
    };
  }, [refresh]);

  const connect = useCallback(async () => {
    const provider = window.ethereum;
    if (!provider) {
      const error: NormalizedError = { code: "wallet_unavailable", message: "Install or enable an injected GenLayer-compatible wallet." };
      setWallet({ available: false, error });
      throw error;
    }
    try {
      const accounts = await provider.request({ method: "eth_requestAccounts" }) as string[];
      await refresh();
      return accounts[0] as `0x${string}` | undefined;
    } catch (error) {
      const normalized = normalizeGenLayerError(error);
      setWallet((previous) => ({ ...previous, error: normalized }));
      throw normalized;
    }
  }, [refresh]);

  const switchToStudioNet = useCallback(async () => {
    const provider = window.ethereum;
    if (!provider) throw { code: "wallet_unavailable", message: "Install or enable an injected wallet." } satisfies NormalizedError;
    try {
      await provider.request({ method: "wallet_switchEthereumChain", params: [{ chainId: studioNetWalletChain.chainId }] });
    } catch (error) {
      const code = typeof error === "object" && error !== null && "code" in error ? (error as { code?: number }).code : undefined;
      if (code !== 4902) throw normalizeGenLayerError(error);
      await provider.request({ method: "wallet_addEthereumChain", params: [studioNetWalletChain] });
    }
    await refresh();
  }, [refresh]);

  return { ...wallet, isStudioNet: wallet.chainId === STUDIO_NET_CHAIN_ID, connect, switchToStudioNet, refresh };
}
