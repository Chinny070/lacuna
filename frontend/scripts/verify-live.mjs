import { createClient } from "genlayer-js";
import { studionet } from "genlayer-js/chains";

const address = process.env.VITE_LACUNA_CONTRACT_ADDRESS ?? "0x964a6e11922F9745d46c906c357dfEDAacC64F91";
const client = createClient({ chain: studionet });
const read = (functionName, args = []) => client.readContract({ address, functionName, args });

const [agreements, constitutions, settlementPolicies] = await Promise.all([
  read("list_agreements"), read("list_constitutions"), read("list_settlement_policies"),
]);
let nonexistentAgreement;
try { await read("get_agreement", ["stage11-nonexistent-record"]); }
catch (error) { nonexistentAgreement = error instanceof Error ? error.message : String(error); }
console.log(JSON.stringify({ address, agreements: String(agreements), constitutions: String(constitutions), settlementPolicies: String(settlementPolicies), nonexistentAgreement }, null, 2));
