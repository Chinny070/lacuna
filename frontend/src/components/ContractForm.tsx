import { useState } from "react";
import { TransactionStatus } from "./TransactionStatus";
import { useLacunaWrite, type WriteKey } from "../hooks/useLacunaWrite";
import { csv } from "../lib/product";

type Field = { label: string; name: string; type: "text" | "number" | "list" | "textarea"; hint?: string; initial?: string };
export type FormSpec = { key: WriteKey; title: string; description: string; fields: Field[]; submit: string };

function coerce(value: string, type: Field["type"]): string | number | string[] { return type === "number" ? Number(value) : type === "list" ? csv(value) : value; }

export function ContractForm({ spec, fixed = {}, onComplete }: { spec: FormSpec; fixed?: Record<string, string>; onComplete?: () => void }) {
  const { wallet, transaction, error, submit } = useLacunaWrite();
  const [values, setValues] = useState<Record<string, string>>(() => Object.fromEntries(spec.fields.map((field) => [field.name, fixed[field.name] ?? field.initial ?? ""])));
  const submitForm = async (event: React.FormEvent) => {
    event.preventDefault();
    const args = spec.fields.map((field) => coerce(values[field.name] ?? "", field.type));
    await submit(spec.key, args);
    onComplete?.();
  };
  return <section className="action-card"><h3>{spec.title}</h3><p>{spec.description}</p><form onSubmit={(event) => void submitForm(event)}>
    {spec.fields.filter((field) => fixed[field.name] === undefined).map((field) => <label key={field.name}>{field.label}{field.type === "textarea" ? <textarea required name={field.name} value={values[field.name] ?? ""} onChange={(event) => setValues({ ...values, [field.name]: event.target.value })} /> : <input required type={field.type === "number" ? "number" : "text"} name={field.name} value={values[field.name] ?? ""} onChange={(event) => setValues({ ...values, [field.name]: event.target.value })} />}{field.hint && <small>{field.hint}</small>}</label>)}
    {!wallet.account && <p className="muted">Connect a StudioNet wallet before submitting.</p>}
    {wallet.account && !wallet.isStudioNet && <p className="error">Switch this wallet to StudioNet before submitting.</p>}
    <button type="submit">{spec.submit}</button>
  </form>{error && <p className="error" role="alert">{error.message}</p>}<TransactionStatus state={transaction} /></section>;
}

export const forms = {
  agreement: { key: "createAgreement", title: "Create an agreement", description: "Lock the parties, evaluation rules, windows, and escrow before work is judged.", submit: "Create agreement", fields: [
    { label: "Agreement ID", name: "agreement_id", type: "text", hint: "A unique permanent identifier." }, { label: "Client wallet", name: "client", type: "text" }, { label: "Contractor wallet", name: "contractor", type: "text" }, { label: "Title", name: "title", type: "text" }, { label: "Obligation", name: "obligation", type: "textarea", hint: "Describe the intervention and intended improvement." }, { label: "Constitution ID", name: "constitution_id", type: "text", hint: "The pre-agreed rules for judging performance." }, { label: "Settlement policy ID", name: "settlement_policy_id", type: "text" }, { label: "Baseline window start", name: "baseline_window_start", type: "number", hint: "Unix timestamp, in seconds." }, { label: "Baseline window end", name: "baseline_window_end", type: "number" }, { label: "Observation window start", name: "observation_window_start", type: "number" }, { label: "Observation window end", name: "observation_window_end", type: "number" }, { label: "Escrow amount", name: "escrow_amount", type: "number", hint: "Whole contract units. LACUNA does not transfer funds in this protocol." },
  ] },
  constitution: { key: "createBaselineConstitution", title: "Create a constitution", description: "Define how any future agreement using this constitution will be judged.", submit: "Publish constitution", fields: [
    { label: "Logical name", name: "name", type: "text" }, { label: "Primary metric", name: "primary_metric", type: "text" }, { label: "Supporting metrics", name: "supporting_metric_schema", type: "list", hint: "Comma-separated." }, { label: "Guardrail metrics", name: "guardrail_metric_schema", type: "list", hint: "Comma-separated." }, { label: "Baseline method", name: "baseline_method", type: "textarea" }, { label: "Required evidence categories", name: "minimum_evidence_categories", type: "list" }, { label: "Minimum independent sources", name: "minimum_independent_sources", type: "number" }, { label: "External shock policy", name: "external_shock_policy", type: "textarea" }, { label: "Attribution rules", name: "attribution_rules", type: "list" }, { label: "Falsification rules", name: "falsification_rules", type: "list" },
  ] },
  policy: { key: "createSettlementPolicy", title: "Create a settlement policy", description: "Specify transparent payment thresholds before the work begins.", submit: "Publish policy", fields: [
    { label: "Logical name", name: "name", type: "text" }, { label: "Minimum performance", name: "minimum_performance_bps", type: "number", hint: "Basis points: 2,500 = 25%." }, { label: "Full-payment threshold", name: "full_payment_threshold_bps", type: "number" }, { label: "Bonus threshold", name: "bonus_threshold_bps", type: "number" }, { label: "Bonus cap", name: "bonus_cap_bps", type: "number" }, { label: "Maximum unresolved confounder", name: "max_unresolved_confounder_bps", type: "number" }, { label: "Guardrail failure cap", name: "guardrail_failure_cap_bps", type: "number" },
  ] },
  baselineEvidence: { key: "submitBaselineEvidence", title: "Add baseline evidence", description: "Evidence is reviewed against the locked constitution before the expected world is estimated.", submit: "Submit baseline evidence", fields: [
    { label: "Evidence ID", name: "evidence_id", type: "text" }, { label: "Agreement ID", name: "agreement_id", type: "text" }, { label: "Source type", name: "source_type", type: "text" }, { label: "Validated source URL", name: "source_url", type: "text" }, { label: "Content hash", name: "content_hash", type: "text" }, { label: "Summary", name: "summary", type: "textarea" }, { label: "Metric reference", name: "metric_ref", type: "text" }, { label: "Period start", name: "period_start", type: "number" }, { label: "Period end", name: "period_end", type: "number" },
  ] },
  outcomeEvidence: { key: "submitOutcomeEvidence", title: "Add outcome evidence", description: "Record what actually happened during the observation window.", submit: "Submit outcome evidence", fields: [
    { label: "Evidence ID", name: "evidence_id", type: "text" }, { label: "Agreement ID", name: "agreement_id", type: "text" }, { label: "Source type", name: "source_type", type: "text" }, { label: "Validated source URL", name: "source_url", type: "text" }, { label: "Content hash", name: "content_hash", type: "text" }, { label: "Summary", name: "summary", type: "textarea" }, { label: "Metric reference", name: "metric_ref", type: "text" }, { label: "Observed value", name: "observed_value_bps", type: "number", hint: "Basis points; 6,100 = 61%." }, { label: "Period start", name: "period_start", type: "number" }, { label: "Period end", name: "period_end", type: "number" },
  ] },
  explanation: { key: "submitAlternativeExplanation", title: "Add a competing explanation", description: "This is a submitted claim, not an attribution verdict.", submit: "Submit explanation", fields: [
    { label: "Explanation ID", name: "explanation_id", type: "text" }, { label: "Agreement ID", name: "agreement_id", type: "text" }, { label: "Explanation type", name: "explanation_type", type: "text", hint: "For example: PRODUCT_LAUNCH or SEASONALITY." }, { label: "Statement", name: "statement", type: "textarea" }, { label: "Evidence references", name: "evidence_refs", type: "list" }, { label: "Affected metrics", name: "affected_metrics", type: "list" }, { label: "Direction", name: "direction", type: "text" }, { label: "Submitted strength", name: "proposed_strength_bps", type: "number", hint: "A claim, in basis points; 4,000 = 40%." },
  ] },
  challenge: { key: "openBaselineChallenge", title: "Challenge the proposed baseline", description: "Point to frozen evidence and a specific methodological concern.", submit: "Open challenge", fields: [
    { label: "Challenge ID", name: "challenge_id", type: "text" }, { label: "Agreement ID", name: "agreement_id", type: "text" }, { label: "Challenge ground", name: "reason_code", type: "text" }, { label: "Statement", name: "statement", type: "textarea" }, { label: "Evidence references", name: "evidence_refs", type: "list" },
  ] },
  appeal: { key: "openAppeal", title: "Appeal a proposed verdict", description: "Appeals preserve the original verdict and ask validators to inspect a specific ground.", submit: "Open appeal", fields: [
    { label: "Appeal ID", name: "appeal_id", type: "text" }, { label: "Agreement ID", name: "agreement_id", type: "text" }, { label: "Appeal ground", name: "ground", type: "text" }, { label: "Statement", name: "statement", type: "textarea" }, { label: "Evidence references", name: "evidence_refs", type: "list" },
  ] },
} satisfies Record<string, FormSpec>;
