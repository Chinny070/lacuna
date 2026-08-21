import { studionet } from "genlayer-js/chains";

const required = (name: "VITE_GENLAYER_RPC_URL" | "VITE_GENLAYER_CHAIN_ID" | "VITE_LACUNA_CONTRACT_ADDRESS", fallback: string): string =>
  import.meta.env[name] ?? fallback;

export const GENLAYER_RPC_URL = required("VITE_GENLAYER_RPC_URL", "https://studio.genlayer.com/api");
export const STUDIO_NET_CHAIN_ID = Number(required("VITE_GENLAYER_CHAIN_ID", "61999"));
export const LACUNA_CONTRACT_ADDRESS = required(
  "VITE_LACUNA_CONTRACT_ADDRESS",
  "0x964a6e11922F9745d46c906c357dfEDAacC64F91",
) as `0x${string}`;

if (!Number.isInteger(STUDIO_NET_CHAIN_ID) || STUDIO_NET_CHAIN_ID !== studionet.id) {
  throw new Error(`LACUNA is configured for StudioNet chain ${studionet.id}, not ${STUDIO_NET_CHAIN_ID}.`);
}

export const studioNetWalletChain = {
  chainId: `0x${STUDIO_NET_CHAIN_ID.toString(16)}`,
  chainName: "GenLayer Studio Network",
  nativeCurrency: { name: "GEN", symbol: "GEN", decimals: 18 },
  rpcUrls: [GENLAYER_RPC_URL],
  blockExplorerUrls: [],
} as const;
