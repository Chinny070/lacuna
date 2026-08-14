import { percent } from "../lib/product";

export function BaselineRange({ baseline, observed }: { baseline?: Record<string, unknown>; observed?: unknown }) {
  if (!baseline) return <section className="range-card"><h3>Counterfactual baseline</h3><p>Once frozen evidence is adjudicated, LACUNA will show the expected range here. It never invents a trajectory.</p></section>;
  const low = Number(baseline.expected_low_bps); const expected = Number(baseline.expected_value_bps); const high = Number(baseline.expected_high_bps);
  return <section className="range-card"><p className="eyebrow">Expected trajectory</p><h3>The world without the intervention</h3><div className="range-axis" aria-label={`Expected range from ${percent(low)} to ${percent(high)}, expected ${percent(expected)}${observed !== undefined ? `, actual ${percent(observed)}` : ""}`}><span className="range-band" style={{ left: `${low / 100}%`, width: `${Math.max(2, (high - low) / 100)}%` }} /><i style={{ left: `${expected / 100}%` }} title="Expected" /><b style={{ left: `${low / 100}%` }}>{percent(low)}</b><b style={{ left: `${high / 100}%` }}>{percent(high)}</b>{observed !== undefined && <em style={{ left: `${Number(observed) / 100}%` }}>Actual {percent(observed)}</em>}</div><table className="sr-only"><caption>Counterfactual baseline values</caption><tbody><tr><th>Expected low</th><td>{percent(low)}</td></tr><tr><th>Expected</th><td>{percent(expected)}</td></tr><tr><th>Expected high</th><td>{percent(high)}</td></tr></tbody></table></section>;
}

export function NegativeSpace({ baseline, observed }: { baseline?: Record<string, unknown>; observed?: unknown }) {
  if (!baseline || observed === undefined) return null;
  return <section className="negative-space"><p className="eyebrow">Preventative / negative-space performance</p><h3>Did an expected harm fail to occur?</h3><p>Expected harmful outcome: {percent(baseline.expected_low_bps)}–{percent(baseline.expected_high_bps)}. Actual: {percent(observed)}.</p><div className="harm-bars" aria-hidden="true"><span style={{ width: `${Math.max(5, Number(baseline.expected_value_bps) / 100)}%` }} /><i style={{ width: `${Math.max(1, Number(observed) / 100)}%` }} /></div><p>This absence is not automatic success. LACUNA still examines whether the contractor credibly contributed after competing explanations and guardrails.</p></section>;
}
