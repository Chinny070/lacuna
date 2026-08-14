export type JsonRecord = Record<string, unknown>;

export function parseContractJson(value: string): JsonRecord | unknown[] | string {
  try { return JSON.parse(value) as JsonRecord | unknown[]; } catch { return value; }
}

export function asRecord(value: unknown): JsonRecord | undefined {
  return typeof value === "object" && value !== null && !Array.isArray(value) ? value as JsonRecord : undefined;
}

export function asList(value: unknown): unknown[] { return Array.isArray(value) ? value : []; }

export function field(record: JsonRecord | undefined, name: string): string {
  const value = record?.[name];
  return value === undefined || value === null ? "—" : String(value);
}

export function percent(value: unknown): string {
  const number = Number(value);
  return Number.isFinite(number) ? `${(number / 100).toLocaleString(undefined, { maximumFractionDigits: 2 })}%` : "—";
}

export function humanize(value: string): string { return value.replaceAll("_", " ").toLowerCase().replace(/\b\w/g, (letter) => letter.toUpperCase()); }
export function csv(value: string): string[] { return value.split(",").map((part) => part.trim()).filter(Boolean); }
export function unix(value: unknown): string { const date = new Date(Number(value) * 1000); return Number.isNaN(date.getTime()) ? "—" : date.toLocaleDateString(); }

export const lifecycle = ["DRAFT", "BASELINE_OPEN", "BASELINE_FROZEN", "BASELINE_PROPOSED", "BASELINE_CHALLENGED", "BASELINE_FINAL", "OBSERVING", "RESOLUTION_OPEN", "RESOLUTION_FROZEN", "VERDICT_PROPOSED", "APPEALED", "FINALIZED"];
