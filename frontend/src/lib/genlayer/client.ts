import { createClient } from "genlayer-js";
import { studionet } from "genlayer-js/chains";
import { LACUNA_CONTRACT_ADDRESS } from "./config";

export const readClient = createClient({ chain: studionet });

export function createWalletClient(account: `0x${string}`, provider: NonNullable<Window["ethereum"]>) {
  return createClient({ chain: studionet, account, provider });
}

export { LACUNA_CONTRACT_ADDRESS };
